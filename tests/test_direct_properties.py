from dataclasses import replace
from datetime import date
from hypothesis import given,settings,strategies as st
from journeydelta.models import Event,TripInstance,InstanceWindow,Horizon,Case,ResolvedCase,SourceRef
from .oracle import brute_force
from .test_direct import key

REF=SourceRef('before','stop_times.txt','a'*64,'data',('t','1'),1,2,0,1)
@settings(max_examples=150,derandomize=True,deadline=None)
@given(st.lists(st.lists(st.tuples(st.sampled_from(['A','B','P']),st.integers(0,9),st.booleans(),st.booleans()),min_size=2,max_size=8),min_size=0,max_size=6))
def test_oracle_permutations_and_addition_monotonicity(rows):
    from journeydelta.direct import choose_direct
    instances=[]
    for n,rs in enumerate(rows):
        clock=0; events=[]
        for seq,(stop,increment,pick,drop) in enumerate(rs):
            clock+=increment
            events.append(Event(stop,seq,clock,clock,pick,drop,False,REF,str(clock),str(clock)))
        instances.append(TripInstance(str(n),'s',date(2026,6,17),None,tuple(events),(REF,),'0'))
    h=Horizon(0,100); c=ResolvedCase(Case('test','','a','b',h),'A','B')
    w=InstanceWindow(tuple(instances),h,(),None,None,0)
    r=choose_direct(w,c).itinerary; expected=brute_force(w,c)
    assert (key(r) if r else None)==expected
    reversed_result=choose_direct(replace(w,instances=tuple(reversed(instances))),c).itinerary
    assert (key(reversed_result) if reversed_result else None)==expected
    if instances:
        reduced=choose_direct(replace(w,instances=tuple(instances[:-1])),c).itinerary
        if reduced: assert r and r.arrival_utc<=reduced.arrival_utc
    if r:
        assert r.board_sequence<r.alight_sequence and r.departure_utc>=0 and r.arrival_utc<=100
        assert r.boardings==1 and r.transfers==0

@settings(max_examples=200,derandomize=True,deadline=None)
@given(st.lists(st.lists(st.tuples(st.sampled_from(['A','B','P']),st.integers(0,9),st.integers(0,5),st.booleans(),st.booleans()),min_size=2,max_size=8),min_size=0,max_size=6),st.integers(0,30),st.integers(31,90))
def test_varied_bounds_dwell_frequency_dates_and_full_replay(rows,start,end):
    from journeydelta.direct import choose_direct
    instances=[]
    for n,rs in enumerate(rows):
        clock=0;events=[]
        for seq,(stop,increment,dwell,pick,drop) in enumerate(rs):
            clock+=increment;arrival=clock;clock+=dwell
            events.append(Event(stop,seq*3+1,arrival,clock,pick,drop,False,REF,str(arrival),str(clock)))
        instances.append(TripInstance(str(n//2),'s',date(2026,6,16+n%2),n*100 if n%3 else None,tuple(events),(REF,),'0'))
    h=Horizon(start,end);c=ResolvedCase(Case('test','','a','b',h),'A','B');w=InstanceWindow(tuple(instances),h,(),None,None,0)
    r=choose_direct(w,c).itinerary;expected=brute_force(w,c)
    assert (key(r) if r else None)==expected
    if r:
        matches=[i for i in instances if (i.trip_id,i.service_date,i.frequency_start)==(r.trip_id,r.service_date,r.frequency_start)]
        assert len(matches)==1
        original=matches[0];a=next(i for i,e in enumerate(original.events) if e.sequence==r.board_sequence);b=next(i for i,e in enumerate(original.events) if e.sequence==r.alight_sequence)
        assert r.events==original.events[a:b+1]
        assert r.events[0].pickup and r.events[-1].drop_off and a<b
        assert r.wait_seconds==r.departure_utc-start and r.ride_seconds==r.arrival_utc-r.departure_utc and r.elapsed_seconds==r.arrival_utc-start
