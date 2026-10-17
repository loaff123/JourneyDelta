from datetime import date
from .support import typed_feed,minimal_feed
from .test_frequencies import frequency_feed

def expanded(tmp_path,feed,horizon,limit=250000):
    from journeydelta.calendars import resolve_coverage
    from journeydelta.frequencies import compile_templates,max_expanded_clock
    from journeydelta.instances import service_dates_for_window,expand_window
    from journeydelta.models import Limits
    from journeydelta.service_time import load_tz_context
    templates=compile_templates(feed).value; tz=load_tz_context(feed.timezone).value
    days=service_dates_for_window(horizon,max_expanded_clock(templates),tz).value
    return expand_window(feed,templates,horizon,days,resolve_coverage(feed,None).value,tz,Limits(expanded_events=limit))

def test_49_hour_date_envelope_and_missing_coverage(tmp_path):
    from journeydelta.models import Horizon
    from journeydelta.suite import instant
    d=minimal_feed(); d['stop_times.txt']=b'trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,49:00:00,49:00:00,A,1\nt,49:30:00,49:30:00,B,2\n'
    f=typed_feed(tmp_path,d).value
    h=Horizon(instant('2026-06-17T01:00:00Z'),instant('2026-06-17T02:00:00Z'))
    r=expanded(tmp_path,f,h); assert not r.has_errors
    assert date(2026,6,15) in r.value.days
    h=Horizon(instant('2026-01-01T01:00:00Z'),instant('2026-01-01T02:00:00Z'))
    r=expanded(tmp_path,f,h); assert r.has_errors and '2025-12-30' in r.diagnostics[0].message

def test_event_cap_counts_before_pruning(tmp_path):
    from journeydelta.models import Horizon
    from journeydelta.suite import instant
    f=frequency_feed(tmp_path,start='00:00:00',end='60:00:01',headway='2')
    h=Horizon(instant('2026-06-17T08:00:00Z'),instant('2026-06-17T09:00:00Z'))
    r=expanded(tmp_path,f,h,10)
    assert r.has_errors and r.diagnostics[0].code=='resource_limit'

def test_exact_instances_independent_identity(tmp_path):
    from journeydelta.models import Horizon
    from journeydelta.suite import instant
    f=frequency_feed(tmp_path); h=Horizon(instant('2026-06-17T07:55:00Z'),instant('2026-06-17T09:00:00Z'))
    r=expanded(tmp_path,f,h)
    assert len(r.value.instances)==3
    assert [i.frequency_start for i in r.value.instances]==[28800,29400,30000]
