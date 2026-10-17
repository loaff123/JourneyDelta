import json
from .support import minimal_feed,typed_feed,base_suite
from .test_instances import expanded

def pair(tmp_path,after=None,before=None):
    from journeydelta.suite import load_suite,resolve_case
    from journeydelta.direct import choose_direct
    from journeydelta.compare import compare_case
    p=tmp_path/'suite.json';p.write_text(json.dumps(base_suite())); s=load_suite(p).value
    feeds=[typed_feed(tmp_path,m,side).value for m,side in [(before,'before'),(after,'after')]]
    windows=[expanded(tmp_path,f,s.cases[0].horizon).value for f in feeds]
    results=[choose_direct(w,resolve_case(s.cases[0],s,f,side).value) for f,w,side in zip(feeds,windows,['before','after'])]
    return feeds,windows,compare_case(*results,s.cases[0])

def test_changed_arrival_and_resolved_source_spans(tmp_path):
    from journeydelta.evidence import build_evidence
    d=minimal_feed();d['stop_times.txt']=d['stop_times.txt'].replace(b'08:30:00',b'09:00:00')
    feeds,windows,result=pair(tmp_path,d)
    e=build_evidence(*feeds,*windows,result)
    assert e.replay['status']=='replayed' and e.replay['arrival_delta_seconds']==1800
    assert any('arrival_time' in x['changed_fields'] for x in e.related_changes)
    for entry in e.records:
        ref=entry['source']; f=feeds[0 if ref.side=='before' else 1]
        assert f.raw.members[ref.member_path][ref.byte_start:ref.byte_end].decode('utf-8')==entry['raw_text']
    assert e.causal_claim=='Related witness changes; not a unique network-wide cause.'

def test_deleted_exception_explicit_absence_and_churn(tmp_path):
    from journeydelta.evidence import build_evidence
    before=minimal_feed(**{'calendar.txt':None,'calendar_dates.txt':b'service_id,date,exception_type\ns,20260617,1\ns,20260618,1\n'})
    after=dict(before);after['calendar_dates.txt']=b'service_id,date,exception_type\ns,20260618,1\n'
    feeds,windows,result=pair(tmp_path,after,before)
    e=build_evidence(*feeds,*windows,result)
    assert any(a['lookup_key']==('s','20260617') for a in e.absence_checks)
    assert result.classification=='lost' and e.replay['status']=='inactive_or_removed_occurrence'
    after=minimal_feed();after['trips.txt']=after['trips.txt'].replace(b',t\n',b',new\n');after['stop_times.txt']=after['stop_times.txt'].replace(b'\nt,',b'\nnew,')
    feeds,windows,result=pair(tmp_path,after)
    assert build_evidence(*feeds,*windows,result).replay['status']=='unavailable_identity_churn'

def test_deleted_cancellation_has_absence_check(tmp_path):
    from journeydelta.evidence import build_evidence
    before=minimal_feed(**{'calendar_dates.txt':b'service_id,date,exception_type\ns,20260617,2\n'})
    feeds,windows,result=pair(tmp_path,minimal_feed(),before)
    e=build_evidence(*feeds,*windows,result)
    assert result.classification=='restored'
    assert any(a['side']=='after' and a['lookup_key']==('s','20260617') for a in e.absence_checks)

def test_inconsistent_source_metadata_rejected(tmp_path):
    from dataclasses import replace
    import pytest
    from journeydelta.evidence import resolve_source
    from journeydelta.models import Invalid
    f=typed_feed(tmp_path).value;s=f.tables['trips.txt'].records[0].source
    for bad in [replace(s,side='after'),replace(s,logical_key=('wrong',)),replace(s,data_ordinal=999),replace(s,physical_lf_line=999),replace(s,record_kind='header',logical_key=None,data_ordinal=None)]:
        with pytest.raises(Invalid): resolve_source(f,bad)

def test_replay_uses_explicit_after_mapping(tmp_path):
    from journeydelta.suite import load_suite,resolve_case
    from journeydelta.direct import choose_direct
    from journeydelta.compare import compare_case
    from journeydelta.evidence import build_evidence
    for keep_original in (True,False):
        before=typed_feed(tmp_path,side='before').value;d=minimal_feed()
        d['stops.txt']+=b'C,NewAlpha,37,-122\nD,NewBeta,38,-123\n'
        if keep_original:
            d['stop_times.txt']+=b't,08:40:00,08:40:00,C,3\nt,08:50:00,08:50:00,D,4\n'
        else:
            d['stop_times.txt']=d['stop_times.txt'].replace(b',A,',b',C,').replace(b',B,',b',D,')
        after=typed_feed(tmp_path,d,side='after').value;s=base_suite();s['places']['a']['after_stop_id']='C';s['places']['b']['after_stop_id']='D'
        path=tmp_path/'mapped.json';path.write_text(json.dumps(s));s=load_suite(path).value
        windows=[expanded(tmp_path,f,s.cases[0].horizon).value for f in (before,after)]
        results=[choose_direct(w,resolve_case(s.cases[0],s,f,side).value) for f,w,side in zip((before,after),windows,('before','after'))]
        comparison=compare_case(*results,s.cases[0]);e=build_evidence(before,after,*windows,comparison)
        assert e.replay['permitted_within_horizon'] is (not keep_original)
