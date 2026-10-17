import json
import pytest
from .support import base_suite, typed_feed, minimal_feed

def load(tmp_path, data):
    from journeydelta.suite import load_suite
    p=tmp_path/'suite.json'; p.write_text(data if isinstance(data,str) else json.dumps(data))
    return load_suite(p)

def test_strict_suite_and_instant(tmp_path):
    result=load(tmp_path,base_suite())
    assert not result.has_errors
    assert result.value.cases[0].horizon.end-result.value.cases[0].horizon.start==4800

@pytest.mark.parametrize('field,value', [('max_transfers',1),('max_transfers',False),('max_transfers',None),('min_change_seconds',0),('depart_after','2026-06-17T08:00:00'),('depart_after','2026-06-17T08:00:00.5Z'),('horizon_end','2026-06-20T08:00:00Z')])
def test_invalid_case(tmp_path,field,value):
    data=base_suite(); data['cases'][0][field]=value
    assert load(tmp_path,data).has_errors

@pytest.mark.parametrize('raw',['{"cases":[],"cases":[1]}','{"x":{"a":1,"a":2}}'])
def test_duplicate_json_keys(tmp_path,raw):
    assert load(tmp_path,raw).diagnostics[0].code=='duplicate_json_key'

def test_empty_unknown_and_boolean_threshold(tmp_path):
    for key,value in [('cases',[]),('model','connections'),('surprise',1)]:
        d=base_suite(); d[key]=value; assert load(tmp_path,d).has_errors
    d=base_suite(); d['cases'][0]['assertions']['max_arrival_delay_seconds']=False
    assert load(tmp_path,d).has_errors

def test_mapping_and_platform_scope(tmp_path):
    from journeydelta.suite import resolve_case
    feed=typed_feed(tmp_path).value; suite=load(tmp_path,base_suite()).value
    assert not resolve_case(suite.cases[0],suite,feed,'before').has_errors
    d=base_suite(); d['places']['a']['after_stop_id']='missing'; suite=load(tmp_path,d).value
    assert resolve_case(suite.cases[0],suite,feed,'after').diagnostics[0].code=='mapping_error'

def test_duplicate_surrogate_key_diagnostic_is_serializable(tmp_path):
    from .test_reports import run
    from journeydelta.app import run_comparison
    from .support import archive
    p=tmp_path/'surrogate.json';p.write_text('{"\\ud800":1,"\\ud800":2}')
    feed=archive(tmp_path,minimal_feed())
    report=run_comparison(feed,feed,p)
    assert report.exit_code==2
    assert report.data['diagnostics'][0]['code']=='duplicate_json_key'
