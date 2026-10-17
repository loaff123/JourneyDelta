from dataclasses import replace
from datetime import date
from .support import typed_feed,minimal_feed,base_suite
from .test_instances import expanded

def evaluate(tmp_path,members=None):
    import json
    from journeydelta.suite import load_suite,resolve_case
    from journeydelta.direct import choose_direct
    f=typed_feed(tmp_path,members).value; p=tmp_path/'suite.json'; p.write_text(json.dumps(base_suite()))
    s=load_suite(p).value; c=resolve_case(s.cases[0],s,f,'before').value
    w=expanded(tmp_path,f,c.case.horizon).value
    return choose_direct(w,c),w,c

def key(itinerary):
    return (itinerary.arrival_utc,itinerary.departure_utc,itinerary.service_date,itinerary.trip_id,itinerary.frequency_start if itinerary.frequency_start is not None else -1,itinerary.board_sequence,itinerary.alight_sequence)

def test_simple_direct_witness(tmp_path):
    from .oracle import brute_force
    r,w,c=evaluate(tmp_path)
    assert key(r.itinerary)==brute_force(w,c)
    assert (r.itinerary.wait_seconds,r.itinerary.ride_seconds,r.itinerary.elapsed_seconds)==(300,1800,2100)
    assert r.itinerary.boardings==1 and r.itinerary.transfers==0

def test_two_trip_connection_never_used(tmp_path):
    d=minimal_feed(); d['trips.txt']=b'route_id,service_id,trip_id,block_id\nr,s,t,block\nr,s,t2,block\n'
    d['stop_times.txt']=b'trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,08:00:00,08:00:00,A,1\nt,08:10:00,08:10:00,P,2\nt2,08:11:00,08:11:00,P,1\nt2,08:20:00,08:20:00,B,2\n'
    assert evaluate(tmp_path,d)[0].itinerary is None

def test_later_express_and_repeated_stop_win(tmp_path):
    d=minimal_feed(); d['trips.txt']=b'route_id,service_id,trip_id\nr,s,t\nr,s,x\n'
    d['stop_times.txt']=b'trip_id,arrival_time,departure_time,stop_id,stop_sequence,pickup_type,drop_off_type,timepoint\nt,08:00:00,08:00:00,A,1,0,0,1\nt,09:00:00,09:00:00,B,2,0,0,1\nx,07:50:00,07:50:00,A,1,0,0,1\nx,08:05:00,08:05:00,A,2,0,0,0\nx,08:35:00,08:35:00,B,3,0,0,1\n'
    r,w,c=evaluate(tmp_path,d)
    assert r.itinerary.trip_id=='x' and r.itinerary.board_sequence==2 and r.itinerary.estimated

def test_boarding_alighting_restrictions(tmp_path):
    for field in ('pickup_type','drop_off_type'):
        d=minimal_feed(); lines=d['stop_times.txt'].decode().splitlines(); lines[0]+=','+field
        lines[1]+=','+('1' if field=='pickup_type' else '0'); lines[2]+=','+('1' if field=='drop_off_type' else '0')
        d['stop_times.txt']=('\n'.join(lines)+'\n').encode()
        assert evaluate(tmp_path,d)[0].itinerary is None
