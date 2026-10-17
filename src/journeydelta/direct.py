"""Linear single-instance scan; no transfer graph or cross-trip continuation."""
from .models import ABSENT_SCOPE,FOUND_SCOPE,DirectResult,Itinerary

def choose_direct(window, case):
    best=None
    winner=None
    for instance in window.instances:
        destination=None
        # Gate guarantees nondecreasing times. The first permitted destination
        # after an origin dominates every later one, including sequence ties.
        for index in range(len(instance.events)-1,-1,-1):
            event=instance.events[index]
            if event.stop_id==case.origin_stop and event.pickup and event.departure>=case.case.horizon.start and destination is not None:
                end_index,end=destination
                candidate=(end.arrival,event.departure,instance.service_date,instance.trip_id,instance.frequency_start if instance.frequency_start is not None else -1,event.sequence,end.sequence)
                if best is None or candidate<best:
                    best=candidate; winner=(instance,index,end_index)
            if event.stop_id==case.destination_stop and event.drop_off and event.arrival<=case.case.horizon.end:
                destination=(index,event)
    if winner is None: return DirectResult(None,ABSENT_SCOPE,case.origin_stop,case.destination_stop)
    instance,a,b=winner; events=instance.events[a:b+1]; start,end=events[0],events[-1]
    sources=instance.sources+tuple(e.source for e in events)
    itinerary=Itinerary(instance.trip_id,instance.service_id,instance.service_date,instance.frequency_start,start.departure,end.arrival,start.departure-case.case.horizon.start,end.arrival-start.departure,end.arrival-case.case.horizon.start,start.sequence,end.sequence,events,sources,any(e.estimated for e in events),instance.wheelchair_accessible)
    return DirectResult(itinerary,FOUND_SCOPE,case.origin_stop,case.destination_stop)
