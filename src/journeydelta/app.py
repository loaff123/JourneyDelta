from dataclasses import replace
from . import __version__
from .archive import read_archive
from .calendars import resolve_coverage
from .capabilities import gate_feed
from .compare import compare_case
from .direct import choose_direct
from .evidence import build_evidence,resolve_source
from .frequencies import compile_templates,max_expanded_clock
from .instances import expand_window,service_dates_for_window
from .models import Diagnostic,Invalid,Limits,MODEL,FOUND_SCOPE
from .report import finalize,diagnostic_exit
from .service_time import load_tz_context,render_instant
from .suite import load_suite,resolve_case

def _base(limits):
    return {'schema_version':'1','tool_version':__version__,'model':MODEL,'scope':FOUND_SCOPE,'limits':limits,
            'gtfs_reference_revision':'2026-04-27','non_evaluated':['multi-leg journeys','transfers and holding','station access/pathways','accessibility routing','fares','realtime','cross-trip block continuations']}

def _accepted(outcome):
    if outcome.has_errors or outcome.value is None:
        raise Invalid(outcome.diagnostics[-1].code,outcome.diagnostics[-1].message,outcome.diagnostics[-1].sources)
    return outcome.value

def _feed_info(feed):
    return {'archive_sha256':feed.raw.archive_sha256,'members':{n:t.raw_member_sha256 for n,t in feed.tables.items()},'excluded_members':feed.raw.excluded_members,'capability_inventory':feed.inventory}

def run_comparison(before_path,after_path,suite_path,limits=Limits()):
    data=_base(limits);diagnostics=[];cases=[];feeds={};suite=None
    try:
        suite=_accepted(load_suite(suite_path)); data['suite_sha256']=suite.sha256;data['origin_urls']=suite.origin_urls
        if len(suite.cases)>limits.cases: raise Invalid('resource_limit','Case count exceeds applied limit')
        for side,path in [('before',before_path),('after',after_path)]:
            read=read_archive(path,side,limits)
            if read.has_errors: diagnostics.extend(read.diagnostics);continue
            gated=gate_feed(read.value);diagnostics.extend(gated.diagnostics)
            if not gated.has_errors: feeds[side]=gated.value
        if len(feeds)!=2:
            return _finish(data,diagnostics,[{'id':c.id,'case':c,'status':'error','diagnostics':[d for d in diagnostics if d.severity=='error']} for c in suite.cases],feeds)
        before,after=feeds['before'],feeds['after']
        if before.timezone!=after.timezone: raise Invalid('unsupported_timezone','Releases have different agency timezones')
        tz=_accepted(load_tz_context(before.timezone)); data['timezone']={'zone':tz.zone,'package_version':tz.package_version,'data_sha256':tz.data_sha256}
        templates={side:_accepted(compile_templates(feed)) for side,feed in feeds.items()}
        common=max(max_expanded_clock(t) for t in templates.values());data['common_max_expanded_clock']=common
        coverage={side:_accepted(resolve_coverage(feed,suite.coverage.get(side))) for side,feed in feeds.items()};data['coverage']=coverage
        cache={}
        for case in suite.cases:
            days=()
            try:
                resolved={side:_accepted(resolve_case(case,suite,feed,side)) for side,feed in feeds.items()}
                days=_accepted(service_dates_for_window(case.horizon,common,tz))
                key=(case.horizon.start,case.horizon.end,days)
                if key not in cache:
                    cache[key]={side:expand_window(feed,templates[side],case.horizon,days,coverage[side],tz,limits) for side,feed in feeds.items()}
                window_errors=[d for o in cache[key].values() for d in o.diagnostics if d.severity=='error']
                if window_errors:
                    diagnostics.extend(window_errors);cases.append({'id':case.id,'case':case,'status':'error','diagnostics':tuple(window_errors),'service_dates':days});continue
                windows={side:_accepted(o) for side,o in cache[key].items()}
                direct={side:choose_direct(w,resolved[side]) for side,w in windows.items()}
                comparison=compare_case(direct['before'],direct['after'],case)
                evidence=build_evidence(before,after,windows['before'],windows['after'],comparison)
                displays={}
                for side,r in direct.items():
                    it=r.itinerary
                    if it:
                        displays[side]={'departure':render_instant(it.departure_utc,tz),'arrival':render_instant(it.arrival_utc,tz),'service_date':it.service_date,
                                        'boarding_accessibility':feeds[side].accessibility[it.events[0].stop_id],'alighting_accessibility':feeds[side].accessibility[it.events[-1].stop_id],
                                        'events':[{'stop_id':e.stop_id,'sequence':e.sequence,'service_arrival_clock':e.arrival_clock,'service_departure_clock':e.departure_clock,'arrival':render_instant(e.arrival,tz),'departure':render_instant(e.departure,tz),'estimated':e.estimated} for e in it.events]}
                cases.append({'id':case.id,'case':case,'status':'pass' if comparison.passed else 'fail','comparison':comparison,'evidence':evidence,'display':displays,'service_dates':days,'expanded_events':{side:w.expanded_events for side,w in windows.items()}})
            except Invalid as exc:
                diagnostics.append(exc.diagnostic);cases.append({'id':case.id,'case':case,'status':'error','diagnostics':(exc.diagnostic,),'service_dates':days})
    except Invalid as exc: diagnostics.append(exc.diagnostic)
    except MemoryError: diagnostics.append(Diagnostic('resource_limit','error','Memory exhausted during comparison'))
    except Exception as exc: diagnostics.append(Diagnostic('internal_error','error',f'{type(exc).__name__}: {exc}'))
    if suite and len(cases)<len(suite.cases):
        completed={c['id'] for c in cases}
        cases.extend({'id':c.id,'case':c,'status':'error','diagnostics':tuple(d for d in diagnostics if d.severity=='error')} for c in suite.cases if c.id not in completed)
    return _finish(data,diagnostics,cases,feeds)

def _finish(data,diagnostics,cases,feeds):
    sources={}
    for d in diagnostics:
        for source in d.sources:
            feed=feeds.get(source.side)
            if feed:
                try:
                    entry=resolve_source(feed,source);sources[entry['anchor']]=entry
                except Invalid: pass # Raw ingestion errors still carry their exact locator.
    data.update(diagnostics=diagnostics,cases=cases,feeds={s:_feed_info(f) for s,f in feeds.items()},diagnostic_evidence=tuple(sources[k] for k in sorted(sources)),
                exit_code=max(diagnostic_exit(diagnostics),1 if any(c['status']=='fail' for c in cases) else 0),
                status='blocked' if diagnostic_exit(diagnostics) else 'evaluated_with_warnings' if diagnostics else 'evaluated')
    return finalize(data)

def run_inspection(feed_path,limits=Limits()):
    data=_base(limits);diagnostics=[]
    try:
        raw=read_archive(feed_path,'inspect',limits);diagnostics.extend(raw.diagnostics)
        if raw.has_errors: return finalize(dict(data,diagnostics=diagnostics,exit_code=diagnostic_exit(diagnostics),status='blocked'),True)
        gate=gate_feed(raw.value);diagnostics=list(gate.diagnostics)
        if gate.has_errors: return finalize(dict(data,diagnostics=diagnostics,exit_code=diagnostic_exit(diagnostics),status='blocked'),True)
        feed=gate.value; data['feed']=_feed_info(feed)
        tz=_accepted(load_tz_context(feed.timezone));data['timezone']={'zone':tz.zone,'package_version':tz.package_version,'data_sha256':tz.data_sha256}
        _accepted(compile_templates(feed))
        cov=resolve_coverage(feed,None)
        if cov.has_errors:
            if cov.diagnostics[0].code=='requires_suite_coverage': diagnostics.append(replace(cov.diagnostics[0],severity='warning'))
            else: diagnostics.extend(cov.diagnostics)
        else: data['coverage']=cov.value
    except Invalid as exc: diagnostics.append(exc.diagnostic)
    except MemoryError: diagnostics.append(Diagnostic('resource_limit','error','Memory exhausted during inspection'))
    except Exception as exc: diagnostics.append(Diagnostic('internal_error','error',f'{type(exc).__name__}: {exc}'))
    data.update(diagnostics=diagnostics,exit_code=diagnostic_exit(diagnostics),status='blocked' if diagnostic_exit(diagnostics) else 'supported with warnings' if diagnostics else 'supported')
    return finalize(data,True)
