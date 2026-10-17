from datetime import date
from .support import typed_feed,minimal_feed

def test_weekly_boundaries_and_exceptions(tmp_path):
    from journeydelta.calendars import active_services
    d=minimal_feed(); d['calendar.txt']=b'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\ns,1,1,1,1,1,0,0,20260615,20260619\n'
    d['calendar_dates.txt']=b'service_id,date,exception_type\ns,20260617,2\ns,20260620,1\n'
    f=typed_feed(tmp_path,d).value
    assert [bool(active_services(f,date(2026,6,n))) for n in (15,17,19,20,21)]==[True,False,True,True,False]
    assert len(active_services(f,date(2026,6,20))[0].sources)==2

def test_exception_only(tmp_path):
    from journeydelta.calendars import active_services
    f=typed_feed(tmp_path,minimal_feed(**{'calendar.txt':None,'calendar_dates.txt':b'service_id,date,exception_type\ns,20260617,1\n'})).value
    assert active_services(f,date(2026,6,17)) and not active_services(f,date(2026,6,18))

def test_coverage_requires_evidence_cannot_broaden(tmp_path):
    from journeydelta.calendars import resolve_coverage
    from journeydelta.models import Coverage
    f=typed_feed(tmp_path).value
    assert resolve_coverage(f,None).value.origin=='publisher'
    assert resolve_coverage(f,Coverage(date(2025,1,1),date(2027,1,1))).has_errors
    assert not resolve_coverage(f,Coverage(date(2026,2,1),date(2026,8,1))).has_errors
    f=typed_feed(tmp_path,minimal_feed(**{'feed_info.txt':None})).value
    assert resolve_coverage(f,None).has_errors
    assert resolve_coverage(f,Coverage(date(2026,1,1),date(2026,12,31))).value.origin=='operator_declared'
