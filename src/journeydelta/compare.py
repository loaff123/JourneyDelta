from .models import CaseComparison,frozen_map

def compare_case(before,after,case):
    old,new=before.itinerary,after.itinerary
    delta=new.arrival_utc-old.arrival_utc if old and new else None
    label=('unchanged' if delta==0 else 'improved' if delta<0 else 'regressed') if delta is not None else 'restored' if new else 'lost' if old else 'both_unreachable'
    assertions={'reachable':'pass' if new else 'fail'}
    if case.arrive_by is not None: assertions['arrive_by']='unavailable' if not new else 'pass' if new.arrival_utc<=case.arrive_by else 'fail'
    if case.max_arrival_delay_seconds is not None: assertions['max_arrival_delay_seconds']='unavailable' if delta is None else 'pass' if delta<=case.max_arrival_delay_seconds else 'fail'
    existing=bool(old and new and case.arrive_by is not None and old.arrival_utc>case.arrive_by and new.arrival_utc>case.arrive_by)
    return CaseComparison(case,before,after,label,frozen_map(assertions),'fail' not in assertions.values(),delta,existing)
