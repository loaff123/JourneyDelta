from .capabilities import clock_seconds,integer
from .models import CLOCK_CAP,Event,Frequency,Invalid,Outcome,TripTemplate

def occurrences(template):
    if not template.frequencies:
        yield None, None
    else:
        for frequency in template.frequencies:
            for start in range(frequency.start, frequency.end, frequency.headway):
                yield start, frequency

def occurrence_starts(template):
    for start, _ in occurrences(template):
        yield start

def compile_templates(feed):
    try:
        grouped={r.get('trip_id'):[] for r in feed.tables['trips.txt'].records}
        for r in feed.tables['stop_times.txt'].records:
            grouped[r.get('trip_id')].append(Event(r.get('stop_id'),integer(r.get('stop_sequence'),'stop_sequence'),clock_seconds(r.get('arrival_time')),clock_seconds(r.get('departure_time')),r.get('pickup_type') in ('','0'),r.get('drop_off_type') in ('','0'),r.get('timepoint')=='0',r.source,r.get('arrival_time'),r.get('departure_time')))
        frequency={t:[] for t in grouped}
        table=feed.tables.get('frequencies.txt')
        for r in table.records if table else ():
            start,end,headway=clock_seconds(r.get('start_time')),clock_seconds(r.get('end_time')),integer(r.get('headway_secs'),'headway_secs',1)
            if end<=start: raise Invalid('invalid_frequency','Frequency end must follow start',(r.source,))
            count=(end-start+headway-1)//headway
            last=start+(count-1)*headway
            if not last<end<last+headway: raise Invalid('invalid_frequency_end','Exact frequency end must be strictly before last departure + headway',(r.source,))
            frequency[r.get('trip_id')].append(Frequency(start,end,headway,count,r.source))
        result=[]
        for r in feed.tables['trips.txt'].records:
            t=r.get('trip_id'); es=tuple(sorted(grouped[t],key=lambda e:e.sequence)); fs=tuple(sorted(frequency[t],key=lambda f:f.start))
            if fs and es[0].arrival!=es[0].departure: raise Invalid('unsupported_frequency_dwell','First frequency arrival must equal departure',(es[0].source,))
            for previous,current in zip(fs,fs[1:]):
                if previous.end>current.start: raise Invalid('invalid_frequency_overlap','Overlapping exact frequency intervals',(previous.source,current.source))
            for f in fs:
                last=f.start+(f.count-1)*f.headway
                if last+es[-1].departure-es[0].departure>CLOCK_CAP: raise Invalid('unsupported_service_clock','Expanded frequency event exceeds 71:59:59',(f.source,es[-1].source))
            result.append(TripTemplate(t,r.get('service_id'),r.get('route_id'),es,fs,r.source,r.get('wheelchair_accessible') or '0'))
        return Outcome(tuple(sorted(result,key=lambda t:t.trip_id)))
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))

def max_expanded_clock(templates):
    values=[0]
    for t in templates:
        if t.frequencies:
            values.extend(f.start+(f.count-1)*f.headway+t.events[-1].departure-t.events[0].departure for f in t.frequencies)
        else: values.append(t.events[-1].departure)
    return max(values)
