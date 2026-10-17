import hashlib
import json
import re
from datetime import datetime, date
from pathlib import Path
from .models import Case, Coverage, Horizon, Invalid, Limits, MODEL, Outcome, ResolvedCase, Suite, frozen_map

def instant(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})',value):
        raise Invalid('invalid_timestamp','Whole-second RFC3339 timestamp with explicit offset required')
    try:
        if value[-1]!='Z' and (int(value[-5:-3])>23 or int(value[-2:])>59): raise ValueError()
        return int(datetime.fromisoformat(value.replace('Z','+00:00')).timestamp())
    except (ValueError, OverflowError) as exc: raise Invalid('invalid_timestamp',f'Invalid timestamp: {value}') from exc

def _keys(obj, allowed, required=()):
    if not isinstance(obj,dict): raise Invalid('invalid_suite','Expected a JSON object')
    if set(obj)-set(allowed) or set(required)-set(obj):
        raise Invalid('invalid_suite',f'Unknown/missing keys: unknown={sorted(set(obj)-set(allowed))}, missing={sorted(set(required)-set(obj))}')

def _string(value):
    if not isinstance(value,str) or not value: raise Invalid('invalid_suite','Nonempty string required')
    return value

def _pairs(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise Invalid('duplicate_json_key',f'Duplicate JSON member: {k!r}')
        d[k]=v
    return d

def _unicode_scalars(value):
    if isinstance(value,str):
        if any(0xD800<=ord(c)<=0xDFFF for c in value):
            raise Invalid('invalid_suite','Unpaired Unicode surrogate is not a scalar string')
    elif isinstance(value,dict):
        for k,v in value.items(): _unicode_scalars(k);_unicode_scalars(v)
    elif isinstance(value,list):
        for v in value: _unicode_scalars(v)

def load_suite(path: Path) -> Outcome[Suite]:
    try:
        # Configuration itself is bounded, independently of declared case count.
        with Path(path).open('rb') as f: raw=f.read(4*1024*1024+1)
        if len(raw)>4*1024*1024: raise Invalid('resource_limit','Suite exceeds 4 MiB input bound')
        d=json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda x: (_ for _ in ()).throw(Invalid('invalid_suite','Nonfinite JSON number')))
        _unicode_scalars(d)
        _keys(d,{'schema_version','model','policy','places','cases','coverage','origin_urls'},{'schema_version','model','policy','places','cases'})
        if d['schema_version']!='1' or d['model']!=MODEL: raise Invalid('unsupported_model','Expected schema 1 and scheduled-direct-v0')
        _keys(d['policy'],{'accessibility'},{'accessibility'})
        if d['policy']['accessibility']!='unconstrained': raise Invalid('unsupported_accessibility_routing','Only unconstrained accessibility is evaluated')
        _keys(d['places'],d['places'])
        places={}
        for alias,p in d['places'].items():
            _string(alias); _keys(p,{'before_stop_id','after_stop_id'},{'before_stop_id','after_stop_id'})
            places[alias]=frozen_map({k:_string(v) for k,v in p.items()})
        if not isinstance(d['cases'],list) or not d['cases']: raise Invalid('invalid_suite','Nonempty cases array required')
        if len(d['cases'])>Limits().cases: raise Invalid('resource_limit','Case count limit exceeded')
        cases=[]; ids=set()
        for c in d['cases']:
            _keys(c,{'id','description','origin','destination','depart_after','horizon_end','max_transfers','assertions'}, {'id','origin','destination','depart_after','horizon_end','max_transfers','assertions'})
            cid=_string(c['id'])
            if cid in ids: raise Invalid('invalid_suite','Duplicate case ID')
            ids.add(cid)
            if type(c['max_transfers']) is not int: raise Invalid('invalid_suite','max_transfers must be integer 0')
            if c['max_transfers']!=0: raise Invalid('unsupported_transfers','Only max_transfers=0 is supported')
            if c['origin'] not in places or c['destination'] not in places: raise Invalid('mapping_error','Unknown place alias')
            start,end=instant(c['depart_after']),instant(c['horizon_end'])
            if not 0<end-start<=48*3600: raise Invalid('invalid_horizon','Require start < end and at most 48 elapsed hours')
            a=c['assertions']; _keys(a,{'reachable','arrive_by','max_arrival_delay_seconds'},{'reachable'})
            if a['reachable'] is not True: raise Invalid('invalid_suite','reachable must be true')
            deadline=instant(a['arrive_by']) if 'arrive_by' in a else None
            if deadline is not None and not start<=deadline<=end: raise Invalid('invalid_suite','arrive_by must be within closed horizon')
            delay=a.get('max_arrival_delay_seconds')
            if 'max_arrival_delay_seconds' in a and (type(delay) is not int or delay<0): raise Invalid('invalid_suite','Delay must be nonnegative integer')
            description=c.get('description','')
            if not isinstance(description,str): raise Invalid('invalid_suite','Description must be string')
            cases.append(Case(cid,description,c['origin'],c['destination'],Horizon(start,end),deadline,delay))
        coverage={}
        if 'coverage' in d:
            _keys(d['coverage'],{'before','after'},{'before','after'})
            for side,v in d['coverage'].items():
                _keys(v,{'start_date','end_date'},{'start_date','end_date'})
                if any(not isinstance(x,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x) for x in v.values()): raise Invalid('invalid_suite','Coverage dates must be YYYY-MM-DD')
                a,b=date.fromisoformat(v['start_date']),date.fromisoformat(v['end_date'])
                if a>b: raise Invalid('invalid_suite','Reversed coverage')
                coverage[side]=Coverage(a,b)
        urls=d.get('origin_urls',{}); _keys(urls,{'before','after'})
        for u in urls.values(): _string(u)
        return Outcome(Suite(tuple(cases),frozen_map(places),frozen_map(coverage),hashlib.sha256(raw).hexdigest(),frozen_map(urls)))
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        return Outcome(None,(Invalid('invalid_suite',str(exc)).diagnostic,))

def resolve_case(case: Case, suite: Suite, feed, side: str) -> Outcome[ResolvedCase]:
    try:
        stops={r.get('stop_id'):r for r in feed.tables['stops.txt'].records}
        ids=[suite.places[a][side+'_stop_id'] for a in (case.origin,case.destination)]
        for stop in ids:
            if stop not in stops: raise Invalid('mapping_error',f'{side}: mapped stop ID {stop!r} missing')
            if stops[stop].get('location_type') not in ('','0'):
                root=stop
                while stops[root].get('parent_station'): root=stops[root].get('parent_station')
                options=sorted(k for k,r in stops.items() if r.get('parent_station')==root and r.get('location_type') in ('','0'))
                raise Invalid('unsupported_endpoint',f'{stop!r} is not a platform; alternatives: {options}',(stops[stop].source,))
        if ids[0]==ids[1]: raise Invalid('invalid_suite','Origin and destination platforms must be distinct')
        return Outcome(ResolvedCase(case,*ids))
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
