from dataclasses import replace
from .test_direct import evaluate

def test_flagship_delay_and_candidate_alternative(tmp_path):
    from journeydelta.compare import compare_case
    r,w,c=evaluate(tmp_path)
    after=replace(r,itinerary=replace(r.itinerary,arrival_utc=r.itinerary.arrival_utc+1800))
    result=compare_case(r,after,c.case)
    assert result.arrival_delta_seconds==1800 and not result.passed
    assert result.assertions['arrive_by']=='fail' and result.assertions['max_arrival_delay_seconds']=='fail'
    after=replace(after,itinerary=replace(after.itinerary,arrival_utc=r.itinerary.arrival_utc+300))
    result=compare_case(r,after,c.case)
    assert result.passed and result.arrival_delta_seconds==300
    after=replace(after,itinerary=replace(after.itinerary,arrival_utc=r.itinerary.arrival_utc+301))
    assert not compare_case(r,after,c.case).passed

def test_absence_classifications_no_infinite_delay(tmp_path):
    from journeydelta.compare import compare_case
    from journeydelta.models import DirectResult,ABSENT_SCOPE
    r,w,c=evaluate(tmp_path); absent=DirectResult(None,ABSENT_SCOPE)
    for old,new,label,passed in [(absent,r,'restored',True),(r,absent,'lost',False),(absent,absent,'both_unreachable',False)]:
        result=compare_case(old,new,c.case)
        assert result.classification==label and result.passed==passed and result.arrival_delta_seconds is None

def test_existing_candidate_deadline_violation(tmp_path):
    from journeydelta.compare import compare_case
    r,w,c=evaluate(tmp_path); late=replace(r,itinerary=replace(r.itinerary,arrival_utc=r.itinerary.arrival_utc+1800))
    result=compare_case(late,late,c.case)
    assert result.existing_deadline_violation and not result.passed
