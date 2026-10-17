import json
from .support import archive,minimal_feed,base_suite

def test_inspection_needs_coverage_and_compare_exit(tmp_path,capsys):
    from journeydelta.cli import main
    p=archive(tmp_path,minimal_feed(**{'feed_info.txt':None}))
    assert main(['inspect',str(p)])==0
    data=json.loads(capsys.readouterr().out)
    assert 'requires_suite_coverage' in {d['code'] for d in data['diagnostics']}
    a=archive(tmp_path,minimal_feed(),'a.zip');b=archive(tmp_path,minimal_feed(),'b.zip')
    suite=tmp_path/'suite.json';suite.write_text(json.dumps(base_suite()))
    assert main(['compare',str(a),str(b),'--suite',str(suite),'--out',str(tmp_path/'out')])==0
    assert (tmp_path/'out'/'junit.xml').exists()

def test_runtime_is_offline(tmp_path,monkeypatch):
    import socket
    def blocked(*a,**k): raise AssertionError('runtime network attempt')
    monkeypatch.setattr(socket,'socket',blocked)
    from .test_reports import run
    assert run(tmp_path).exit_code==0

def test_render_and_finalize_resource_failures_exit_three(tmp_path,monkeypatch,capsys):
    from journeydelta import cli,app
    a=archive(tmp_path,minimal_feed(),'a.zip');b=archive(tmp_path,minimal_feed(),'b.zip');s=tmp_path/'s.json';s.write_text(json.dumps(base_suite()))
    args=['compare',str(a),str(b),'--suite',str(s),'--out',str(tmp_path/'output')]
    real=cli.render_reports
    def exhausted(*a,**k): raise MemoryError()
    monkeypatch.setattr(cli,'render_reports',exhausted)
    assert cli.main(args)==3
    monkeypatch.setattr(cli,'render_reports',real);monkeypatch.setattr(app,'finalize',exhausted)
    assert cli.main(args)==3
