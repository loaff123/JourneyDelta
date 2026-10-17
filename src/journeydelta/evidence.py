"""Source resolution and stable-key witness replay, never unique causality."""
import hashlib
import json
from .models import EvidenceIndex,Invalid,frozen_map

def source_anchor(source):
    identity=(source.side,source.member_path,source.member_sha256,source.byte_start,source.byte_end)
    return 'source-'+hashlib.sha256(json.dumps(identity,separators=(',',':')).encode()).hexdigest()[:24]

def resolve_source(feed,source):
    raw=feed.raw.members.get(source.member_path)
    if raw is None or hashlib.sha256(raw).hexdigest()!=source.member_sha256 or not 0<=source.byte_start<source.byte_end<=len(raw):
        raise Invalid('internal_error','Unresolvable source locator',(source,))
    if source.side!=feed.raw.side or source.physical_lf_line!=raw[:source.byte_start].count(b'\n')+1 or (source.byte_start and raw[source.byte_start-1]!=10):
        raise Invalid('internal_error','Inconsistent source identity or boundary',(source,))
    line_end=raw.find(b'\n',source.byte_start)
    if source.byte_end!=(line_end+1 if line_end>=0 else len(raw)):
        raise Invalid('internal_error','Source does not cover one complete physical record',(source,))
    fields={}
    if source.record_kind=='data':
        table=feed.tables.get(source.member_path)
        record=next((r for r in table.records if r.source.byte_start==source.byte_start and r.source.byte_end==source.byte_end),None) if table else None
        if record is None: raise Invalid('internal_error','Source is not a complete data record',(source,))
        if source!=record.source: raise Invalid('internal_error','Inconsistent data source metadata',(source,))
        fields=record.fields
    else:
        def content(chunk):
            return chunk.removesuffix(b'\n').removesuffix(b'\r\r').removesuffix(b'\r').removeprefix(b'\xef\xbb\xbf')
        body=content(raw[source.byte_start:source.byte_end])
        prior=raw[:source.byte_start].splitlines(keepends=True)
        expected='blank' if body==b'' else 'header' if not any(content(x) for x in prior) else 'data'
        if source.record_kind!=expected or source.logical_key is not None or source.data_ordinal is not None:
            raise Invalid('internal_error','Inconsistent non-data source metadata',(source,))
    return frozen_map({'anchor':source_anchor(source),'source':source,'fields':fields,'raw_text':raw[source.byte_start:source.byte_end].decode('utf-8')})

def _supplement(feed,itinerary):
    if not itinerary: return ()
    refs=[];trip=next(r for r in feed.tables['trips.txt'].records if r.get('trip_id')==itinerary.trip_id)
    route=next(r for r in feed.tables['routes.txt'].records if r.get('route_id')==trip.get('route_id'))
    refs.append(route.source)
    refs.extend(r.source for r in feed.tables['agency.txt'].records if not route.get('agency_id') or r.get('agency_id')==route.get('agency_id'))
    for event in itinerary.events:
        refs.extend(feed.accessibility[event.stop_id]['sources'])
    fi=feed.tables.get('feed_info.txt')
    if fi: refs.extend(r.source for r in fi.records)
    return tuple(refs)

def _replay(after,window,result):
    old=result.before.itinerary
    if not old: return frozen_map({'status':'no_before_witness'})
    if not any(r.get('trip_id')==old.trip_id for r in after.tables['trips.txt'].records): return frozen_map({'status':'unavailable_identity_churn'})
    match=next((i for i in window.instances if (i.trip_id,i.service_date,i.frequency_start)==(old.trip_id,old.service_date,old.frequency_start)),None)
    if match is None: return frozen_map({'status':'inactive_or_removed_occurrence'})
    board=next((e for e in match.events if e.sequence==old.board_sequence),None)
    alight=next((e for e in match.events if e.sequence==old.alight_sequence),None)
    if board is None or alight is None: return frozen_map({'status':'unavailable_identity_churn'})
    if result.after.origin_stop is None or result.after.destination_stop is None:
        return frozen_map({'status':'unavailable_mapping_context'})
    reasons=[]
    if board.stop_id!=result.after.origin_stop: reasons.append('boarding_stop_does_not_match_after_mapping')
    if alight.stop_id!=result.after.destination_stop: reasons.append('alighting_stop_does_not_match_after_mapping')
    if not board.pickup: reasons.append('boarding_not_permitted')
    if not alight.drop_off: reasons.append('alighting_not_permitted')
    if board.departure<result.case.horizon.start: reasons.append('departure_before_horizon')
    if alight.arrival>result.case.horizon.end: reasons.append('arrival_after_horizon')
    return frozen_map({'status':'replayed','permitted_within_horizon':not reasons,'reasons':tuple(reasons),'departure_utc':board.departure,'arrival_utc':alight.arrival,'arrival_delta_seconds':alight.arrival-old.arrival_utc,'sources':match.sources+(board.source,alight.source)})

def build_evidence(before,after,before_window,after_window,result):
    feeds={'before':before,'after':after};records={};absences={};changes={}
    indexes={side:{name:{r.source.logical_key:r for r in table.records} for name,table in f.tables.items()} for side,f in feeds.items()}
    seeds=[]
    for side,direct in [('before',result.before),('after',result.after)]:
        it=direct.itinerary
        if it: seeds.extend(it.sources+_supplement(feeds[side],it))
    replay=_replay(after,after_window,result)
    seeds.extend(replay.get('sources',()))
    # Inactive calendar removals are relevant even though active_services omits them.
    for f,window in [(before,before_window),(after,after_window)]:
        relevant={it.service_id for it in (result.before.itinerary,result.after.itinerary) if it}
        dates={d.strftime('%Y%m%d') for d in window.days}
        table=f.tables.get('calendar_dates.txt')
        for r in table.records if table else ():
            if r.get('service_id') in relevant and r.get('date') in dates:
                seeds.append(r.source)
    for source in seeds:
        f=feeds[source.side]; entry=resolve_source(f,source); source=entry['source']; records[entry['anchor']]=entry
        other='after' if source.side=='before' else 'before'; target=feeds[other]
        counterpart=indexes[other].get(source.member_path,{}).get(source.logical_key)
        if counterpart:
            other_entry=resolve_source(target,counterpart.source); records[other_entry['anchor']]=other_entry
            old,new=(entry,other_entry) if source.side=='before' else (other_entry,entry)
            changed=tuple(sorted(k for k in set(old['fields'])|set(new['fields']) if old['fields'].get(k)!=new['fields'].get(k)))
            if changed: changes[(source.member_path,source.logical_key)]=frozen_map({'member_path':source.member_path,'logical_key':source.logical_key,'before_anchor':old['anchor'],'after_anchor':new['anchor'],'changed_fields':changed})
        else:
            table=target.tables.get(source.member_path)
            absence=frozen_map({'side':other,'member_path':source.member_path,'lookup_key':source.logical_key,'member_sha256':table.raw_member_sha256 if table else None,'archive_sha256':target.raw.archive_sha256,'complete_table_searched':table is not None,'table_absent':table is None,'related_anchor':entry['anchor']})
            absences[(other,source.member_path,source.logical_key)]=absence
    return EvidenceIndex(tuple(records[k] for k in sorted(records)),tuple(absences[k] for k in sorted(absences)),tuple(changes[k] for k in sorted(changes)),replay)
