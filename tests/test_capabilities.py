import pytest
from .support import typed_feed, minimal_feed

def test_core_feed_supported(tmp_path):
    result=typed_feed(tmp_path)
    assert not result.has_errors, result.diagnostics
    assert result.value.timezone=='Etc/UTC'
    assert result.value.tables['trips.txt'].records[0].source.logical_key==('t',)

@pytest.mark.parametrize('value,allowed',[('0',True),('1',False),('2',False),('x',False)])
def test_rider_restriction(tmp_path,value,allowed):
    data=minimal_feed(); data['routes.txt']=f'route_id,agency_id,route_type,eligibility_restricted\nr,ag,2,{value}\n'.encode()
    assert (not typed_feed(tmp_path,data).has_errors)==allowed

@pytest.mark.parametrize('table,raw',[
 ('route_attributes.txt',b'route_id,category,new_field\nr,1,value\n'),
 ('unknown.txt',b'id\n'),
 ('pathways.txt',b'pathway_id\nx\n'),
 ('areas.txt',b'area_id,wkt\nx,stuff\n'),
 ('trips.txt',b'route_id,service_id,trip_id\nr,s,t\nr,s,t\n'),
 ('stop_times.txt',b'trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,08:00:00,08:00:00,A,1\nt,,08:30:00,B,2\n'),
 ('stop_times.txt',b'trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,08:00:00,08:00:00,A,1\nt,08:30:00,08:30:00,B,1\n'),
 ('calendar_dates.txt',b'service_id,date,exception_type\ns,20260617,1\ns,20260617,1\n'),
 ('transfers.txt',b'from_stop_id,to_stop_id,transfer_type\nA,B,2\n')])
def test_invalid_or_unsupported_data(tmp_path,table,raw):
    d=minimal_feed(); d[table]=raw
    assert typed_feed(tmp_path,d).has_errors

def test_transfers_disclosed_not_applied_and_unknown_empty_warns(tmp_path):
    d=minimal_feed(); d['transfers.txt']=b'from_stop_id,to_stop_id,transfer_type\nA,B,1\nB,B,3\n'
    d['routes.txt']=b'route_id,agency_id,route_type,unknown\nr,ag,2,\n'
    r=typed_feed(tmp_path,d)
    assert not r.has_errors
    assert {'transfer_semantics_not_evaluated','ignored_empty_column'} <= {x.code for x in r.diagnostics}

def test_accessibility_inheritance_and_legacy_namespace(tmp_path):
    d=minimal_feed(); d['stops.txt']=b'stop_id,location_type,parent_station,wheelchair_boarding\nS,1,,1\nA,0,S,0\nB,0,S,2\n'
    d['stop_attributes.txt']=b'stop_id,accessibility_id\nA,2\n'
    r=typed_feed(tmp_path,d); assert not r.has_errors
    assert r.value.accessibility['A']['standard_effective']=='1'
    assert r.value.accessibility['B']['standard_effective']=='2'
    assert r.value.accessibility['A']['legacy_accessibility_id']=='2'

def test_unresolved_ancestor_and_huge_integer_are_diagnostics(tmp_path):
    d=minimal_feed(); d['stops.txt']=b'stop_id,location_type,parent_station\nA,0,S\nB,0,\nS,1,MISSING\n'
    r=typed_feed(tmp_path,d); assert r.has_errors and r.diagnostics[-1].sources
    d=minimal_feed(); d['stop_times.txt']=('trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,08:00:00,08:00:00,A,'+'9'*4301+'\nt,08:30:00,08:30:00,B,2\n').encode()
    r=typed_feed(tmp_path,d); assert r.has_errors and r.diagnostics[-1].sources

def test_trip_qualified_transfers_and_default_type(tmp_path):
    for raw in (b'from_trip_id,to_trip_id,transfer_type\nt,t,4\n',b'from_stop_id,to_stop_id,transfer_type\nA,B,\n'):
        d=minimal_feed(); d['transfers.txt']=raw
        assert not typed_feed(tmp_path,d).has_errors
    d=minimal_feed(); d['transfers.txt']=b'from_stop_id,to_stop_id,transfer_type\nA,B,4\n'
    assert typed_feed(tmp_path,d).has_errors

def test_table_errors_never_borrow_unrelated_record_source(tmp_path):
    d=minimal_feed();d['routes.txt']=b'route_id,agency_id\nr,ag\n'
    result=typed_feed(tmp_path,d)
    assert result.has_errors
    assert all(s.member_path=='routes.txt' for s in result.diagnostics[-1].sources)
    d=minimal_feed();d['agency.txt']=b'agency_id,agency_name,agency_url,agency_timezone\n'
    result=typed_feed(tmp_path,d)
    assert result.has_errors
    assert all(s.member_path=='agency.txt' for s in result.diagnostics[-1].sources)
