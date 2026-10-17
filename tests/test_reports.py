import json
import xml.etree.ElementTree as ET
from .support import archive,minimal_feed,base_suite

def run(tmp_path,after=None,suite=None):
    from journeydelta.app import run_comparison
    from journeydelta.models import Limits
    a=archive(tmp_path,minimal_feed(),'before.zip'); b=archive(tmp_path,after or minimal_feed(),'after.zip')
    p=tmp_path/'suite.json';p.write_text(json.dumps(suite or base_suite()))
    return run_comparison(a,b,p,Limits())

def test_four_renderers_saved_object_and_scope(tmp_path):
    from journeydelta.render import render_reports
    report=run(tmp_path); assert report.exit_code==0
    files=render_reports(report)
    assert set(files)=={'report.json','report.html','junit.xml','summary.txt'}
    data=json.loads(files['report.json']); assert data['schema_version']=='1' and data['model']=='scheduled-direct-v0'
    assert data['cases'][0]['comparison']['after']['itinerary']['arrival_utc']==1781685000
    assert 'Single boarding only. Multi-leg journeys were not evaluated.' in files['report.html'].decode()
    assert ET.fromstring(files['junit.xml']).attrib['failures']=='0'
    assert data['canonical_digest'] and data['timezone']['package_version']=='2026.5'

def test_warning_propagation_and_safe_html(tmp_path):
    from journeydelta.render import render_reports
    d=minimal_feed();d['trips.txt']=d['trips.txt'].replace(b'\n',b'\r\r\n')
    s=base_suite();s['cases'][0]['description']='<script>alert("x")</script>';s['origin_urls']={'before':'javascript:alert(1)','after':'https://example.org/?q=<x>'}
    files=render_reports(run(tmp_path,d,s))
    for data in files.values(): assert b'nonstandard_crcrlf' in data
    html=files['report.html'].decode();assert '<script>' not in html and 'href="javascript:' not in html and '&lt;script&gt;' in html
    assert 'src=' not in html and '<script' not in html
    assert 'https://example.org/?q=&lt;x&gt;' in html

def test_case_mapping_errors_do_not_become_green_skips(tmp_path):
    from journeydelta.render import render_reports
    s=base_suite();s['places']['bad']={'before_stop_id':'A','after_stop_id':'MISSING'}
    c=dict(s['cases'][0]);c.update(id='bad',origin='bad');s['cases'].append(c)
    r=run(tmp_path,suite=s);assert r.exit_code==2
    tree=ET.fromstring(render_reports(r)['junit.xml']);assert tree.attrib['errors']=='1' and not tree.findall('.//skipped')

def test_xml_control_characters_and_lone_surrogates(tmp_path):
    from journeydelta.render import render_reports
    s=base_suite();s['cases'][0]['id']='bad\x01id'
    r=run(tmp_path,suite=s);ET.fromstring(render_reports(r)['junit.xml'])
    s['cases'][0]['id']='bad\ud800id'
    r=run(tmp_path,suite=s);assert r.exit_code==2

def test_observed_resource_error_takes_precedence(tmp_path):
    from journeydelta.app import run_comparison
    from journeydelta.models import Limits
    before=minimal_feed();before['feed_info.txt']=before['feed_info.txt'].replace(b'20261231',b'20260616')
    a=archive(tmp_path,before,'old.zip');b=archive(tmp_path,minimal_feed(),'new.zip');s=tmp_path/'s.json';s.write_text(json.dumps(base_suite()))
    r=run_comparison(a,b,s,Limits(expanded_events=1))
    assert r.exit_code==3
    assert {'coverage_error','resource_limit'} <= {d['code'] for d in r.data['diagnostics']}
    assert r.data['cases'][0]['service_dates']

def test_internal_failure_keeps_remaining_cases_as_junit_errors(tmp_path,monkeypatch):
    from journeydelta import app
    from journeydelta.render import render_reports
    s=base_suite();s['cases'].append(dict(s['cases'][0],id='second'))
    real=app.choose_direct;count=0
    def failure(*a):
        nonlocal count
        count+=1
        if count==3: raise MemoryError()
        return real(*a)
    monkeypatch.setattr(app,'choose_direct',failure)
    r=run(tmp_path,suite=s);assert r.exit_code==3 and len(r.data['cases'])==2
    assert ET.fromstring(render_reports(r)['junit.xml']).attrib['errors']=='1'

def test_saved_report_is_deeply_immutable(tmp_path):
    import pytest
    r=run(tmp_path)
    with pytest.raises(TypeError): r.data['cases'][0]['status']='fail'

def test_all_formats_preserve_global_provenance(tmp_path):
    from journeydelta.render import render_reports
    r=run(tmp_path);files=render_reports(r)
    for filename in ('report.html','junit.xml','summary.txt'):
        assert r.data['suite_sha256'].encode() in files[filename]
        assert r.data['timezone']['data_sha256'].encode() in files[filename]
        assert b'stop_times.txt' in files[filename]

def test_report_matches_published_schema(tmp_path):
    from pathlib import Path
    import jsonschema
    from journeydelta.report import primitive
    schema=json.loads((Path(__file__).parents[1]/'schemas/report-v1.schema.json').read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(primitive(run(tmp_path).data),schema)

def test_csv_order_and_zip_container_changes_keep_metrics(tmp_path):
    from journeydelta.app import run_comparison
    d=minimal_feed()
    for name,raw in d.items():
        lines=raw.splitlines();d[name]=b'\n'.join([lines[0],*reversed(lines[1:])])+b'\n'
    r=run(tmp_path,after=d)
    assert r.exit_code==0
    assert r.data['cases'][0]['comparison']['arrival_delta_seconds']==0
    assert not r.data['cases'][0]['evidence']['related_changes']

def test_html_fragment_navigation_has_no_missing_targets(tmp_path):
    from html.parser import HTMLParser
    from journeydelta.render import render_reports
    class Links(HTMLParser):
        def __init__(self): super().__init__();self.ids=set();self.links=[]
        def handle_starttag(self,tag,attrs):
            attrs=dict(attrs)
            if 'id' in attrs:self.ids.add(attrs['id'])
            if 'href' in attrs:self.links.append(attrs['href'])
            assert tag not in ('script','img','iframe','object','embed','link')
            assert not any(k.startswith('on') for k in attrs)
    p=Links();p.feed(render_reports(run(tmp_path))['report.html'].decode())
    assert p.links and all(h[1:] in p.ids for h in p.links if h.startswith('#'))
