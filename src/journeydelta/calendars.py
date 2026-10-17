from .capabilities import date_value
from .models import Activation,Coverage,Invalid,Outcome

DAYS=('monday','tuesday','wednesday','thursday','friday','saturday','sunday')

def active_services(feed, day):
    weekly=feed.tables.get('calendar.txt'); exceptions=feed.tables.get('calendar_dates.txt')
    state={}; evidence={}
    for r in weekly.records if weekly else ():
        sid=r.get('service_id'); evidence[sid]=[r.source]
        state[sid]=date_value(r.get('start_date'))<=day<=date_value(r.get('end_date')) and r.get(DAYS[day.weekday()])=='1'
    for r in exceptions.records if exceptions else ():
        if date_value(r.get('date'))==day:
            sid=r.get('service_id'); state[sid]=r.get('exception_type')=='1'; evidence.setdefault(sid,[]).append(r.source)
    return tuple(Activation(sid,day,tuple(evidence[sid])) for sid in sorted(state) if state[sid])

def resolve_coverage(feed, supplied):
    try:
        table=feed.tables.get('feed_info.txt'); row=table.records[0] if table and table.records else None
        a=date_value(row.get('feed_start_date')) if row and row.get('feed_start_date') else None
        b=date_value(row.get('feed_end_date')) if row and row.get('feed_end_date') else None
        refs=(row.source,) if row else ()
        if supplied:
            if (a and supplied.start_date<a) or (b and supplied.end_date>b): raise Invalid('coverage_conflict','Suite coverage cannot broaden publisher coverage',refs)
            return Outcome(Coverage(supplied.start_date,supplied.end_date,'operator_narrowed_publisher' if a and b else 'operator_declared',refs))
        if a and b: return Outcome(Coverage(a,b,'publisher',refs))
        raise Invalid('requires_suite_coverage','Publisher coverage incomplete; explicit before/after suite coverage required',refs)
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
