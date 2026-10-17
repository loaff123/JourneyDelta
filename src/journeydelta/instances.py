from dataclasses import replace
from datetime import datetime,timedelta,timezone
from .calendars import active_services
from .frequencies import occurrences
from .models import InstanceWindow,Invalid,Outcome,TripInstance
from .service_time import service_origin_utc

def service_dates_for_window(horizon,common_max_clock,tz):
    try:
        first=datetime.fromtimestamp(horizon.start-common_max_clock,timezone.utc).date()-timedelta(days=1)
        last=datetime.fromtimestamp(horizon.end,timezone.utc).date()+timedelta(days=1)
        dates=[]; day=first
        while day<=last:
            result=service_origin_utc(day,tz)
            if result.has_errors: return Outcome(None,result.diagnostics)
            origin=result.value
            if origin<=horizon.end and origin+common_max_clock>=horizon.start: dates.append(day)
            day+=timedelta(days=1)
        return Outcome(tuple(dates))
    except (ValueError,OverflowError) as exc: return Outcome(None,(Invalid('unsupported_date',str(exc)).diagnostic,))

def expand_window(feed,templates,horizon,days,coverage,tz,limits):
    try:
        missing=[d.isoformat() for d in days if not coverage.start_date<=d<=coverage.end_date]
        if missing: raise Invalid('coverage_error',f'{feed.raw.side}: missing required service dates: {", ".join(missing)}',coverage.sources)
        work=[]; count=0
        for day in days:
            active={a.service_id:a for a in active_services(feed,day)}
            origin=service_origin_utc(day,tz)
            if origin.has_errors: return Outcome(None,origin.diagnostics)
            for t in templates:
                if t.service_id not in active: continue
                occurrence_count=sum(f.count for f in t.frequencies) if t.frequencies else 1
                count+=occurrence_count*len(t.events)
                if count>limits.expanded_events: raise Invalid('resource_limit',f'Expanded stop events {count} exceed {limits.expanded_events}; counted before pruning')
                work.append((day,origin.value,t,active[t.service_id]))
        instances=[]
        for day,origin,t,activation in work:
            for start, freq in occurrences(t):
                shift=origin+(start-t.events[0].departure if start is not None else 0)
                events=tuple(replace(e,arrival=e.arrival+shift,departure=e.departure+shift) for e in t.events)
                refs=(t.source,)+activation.sources+((freq.source,) if freq else ())
                instances.append(TripInstance(t.trip_id,t.service_id,day,start,events,refs,t.wheelchair_accessible))
        return Outcome(InstanceWindow(tuple(instances),horizon,days,coverage,tz,count))
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
