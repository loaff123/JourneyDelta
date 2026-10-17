"""Optional local real-data integration. No Caltrain member bytes are distributed."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest
from .support import archive

ROOT=Path(__file__).parents[1]
_configured_root=os.environ.get('JOURNEYDELTA_CALTRAIN_ROOT')
DATA=Path(_configured_root) if _configured_root else None
CLI=Path(os.environ.get('JOURNEYDELTA_CLI',ROOT/'.installed'/'bin'/'journeydelta'))
pytestmark=pytest.mark.skipif(
    DATA is None or not all((DATA/name).is_dir() for name in ('caltrain-before','caltrain-after')),
    reason='Set JOURNEYDELTA_CALTRAIN_ROOT explicitly to available rights-controlled historical fixture directories',
)

@pytest.fixture(scope='module')
def pinned(tmp_path_factory):
    tmp=tmp_path_factory.mktemp('caltrain-installed')
    manifest=json.loads((ROOT/'tests/fixtures/caltrain/source-manifest.json').read_text())
    members={'before':{},'after':{}}
    for item in manifest['files']:
        raw=(DATA/('caltrain-'+item['side'])/item['file']).read_bytes()
        assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        members[item['side']][item['file']]=raw
    paths={side:archive(tmp,data,side+'.zip') for side,data in members.items()}
    return tmp,paths,members

def suite(start='2026-06-17T08:00:00Z',end='2026-06-17T10:00:00Z',deadline='2026-06-17T09:30:00Z'):
    return {'schema_version':'1','model':'scheduled-direct-v0','policy':{'accessibility':'unconstrained'},'places':{'a':{'before_stop_id':'70211','after_stop_id':'70211'},'b':{'before_stop_id':'70011','after_stop_id':'70011'}},'cases':[{'id':'event_night_late_return','origin':'a','destination':'b','depart_after':start,'horizon_end':end,'max_transfers':0,'assertions':{'reachable':True,'arrive_by':deadline}}]}

def compare(pinned,name,config=None,reverse=False,after_path=None):
    tmp,paths,members=pinned;p=tmp/(name+'.json');p.write_text(json.dumps(config or suite()));out=tmp/name
    a,b=(paths['after'],paths['before']) if reverse else (paths['before'],after_path or paths['after'])
    completed=subprocess.run([str(CLI),'compare',str(a),str(b),'--suite',str(p),'--out',str(out)],capture_output=True,text=True,timeout=30)
    assert (out/'report.json').exists(),completed.stderr
    return completed.returncode,json.loads((out/'report.json').read_text()),out

def test_V01_inspect_untouched_and_warning_locators(pinned):
    for side in ('before','after'):
        completed=subprocess.run([str(CLI),'inspect',str(pinned[1][side])],capture_output=True,text=True,timeout=30)
        assert completed.returncode==0,completed.stdout+completed.stderr
        data=json.loads(completed.stdout);assert data['status']=='supported with warnings'
        transfer=next(x for x in data['diagnostics'] if x['code']=='transfer_semantics_not_evaluated');assert len(transfer['sources'])==2
        if side=='after':
            warning=next(x for x in data['diagnostics'] if x['code']=='nonstandard_crcrlf')
            assert len(warning['sources'])==261 and warning['sources'][0]['data_ordinal'] is None

def test_V02_V07_overnight_metrics_and_exact_sources(pinned):
    code,data,out=compare(pinned,'forward');assert code==0
    c=data['cases'][0];assert c['comparison']['before']['itinerary'] is None
    it=c['comparison']['after']['itinerary']
    assert (it['trip_id'],it['service_date'],it['departure_utc'],it['arrival_utc'],it['wait_seconds'],it['ride_seconds'],it['elapsed_seconds'])==('905','2026-06-16',1781685000,1781688600,1800,3600,5400)
    sources=[r['source'] for r in c['evidence']['records'] if r['source']['side']=='after']
    for member,key,line in [('trips.txt',['905'],154),('calendar_dates.txt',['c_71906_b_none_d_0','20260616'],2),('stop_times.txt',['905','1'],5434),('stop_times.txt',['905','18'],5451)]:
        assert any(s['member_path']==member and s['logical_key']==key and s['physical_lf_line']==line for s in sources),(member,key,line)

def test_V03_reverse_lost(pinned):
    code,data,out=compare(pinned,'reverse',reverse=True)
    assert code==1 and data['cases'][0]['comparison']['classification']=='lost'
    assert any(a['lookup_key']==['c_71906_b_none_d_0','20260616'] for a in data['cases'][0]['evidence']['absence_checks'])

def test_V04_earlier_train(pinned):
    code,data,out=compare(pinned,'earlier',suite('2026-06-17T07:20:00Z','2026-06-17T09:00:00Z','2026-06-17T09:00:00Z'))
    assert code==0 and data['cases'][0]['comparison']['after']['itinerary']['trip_id']=='903'

def test_V05_valid_cancellation_and_undefined_service_deletion(pinned):
    tmp,paths,members=pinned
    for mode in ('remove','cancel'):
        after=dict(members['after']);lines=after['calendar_dates.txt'].splitlines(keepends=True)
        after['calendar_dates.txt']=b''.join((line.rsplit(b'1',1)[0]+b'2\n') if mode=='cancel' and line.startswith(b'c_71906_b_none_d_0,20260616,') else line for line in lines if mode!='remove' or not line.startswith(b'c_71906_b_none_d_0,20260616,'))
        path=archive(tmp,after,'synthetically-modified-'+mode+'.zip')
        code,data,out=compare(pinned,'mutation-'+mode,after_path=path)
        assert code==(2 if mode=='remove' else 1)
        if mode=='remove': assert any(d['code']=='unresolved_reference' for d in data['diagnostics'])
        else: assert data['cases'][0]['comparison']['after']['itinerary'] is None

def test_V06_coverage_is_not_restoration(pinned):
    code,data,out=compare(pinned,'coverage',suite('2026-09-17T08:00:00Z','2026-09-17T10:00:00Z','2026-09-17T09:30:00Z'))
    assert code==2 and any(d['code']=='coverage_error' for d in data['diagnostics'])
