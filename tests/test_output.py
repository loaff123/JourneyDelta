import pytest
from .support import archive,minimal_feed

def test_disjoint_symlink_and_existing_paths(tmp_path):
    from journeydelta.output import write_reports
    p=archive(tmp_path,minimal_feed()); original=p.read_bytes()
    assert write_reports({'report.json':b'new'},p,True,(p,)).has_errors
    out=tmp_path/'out';out.mkdir()
    assert write_reports({'report.json':b'new'},out,False,(p,)).has_errors
    link=tmp_path/'link';link.symlink_to(out,target_is_directory=True)
    assert write_reports({'report.json':b'new'},link,True,(p,)).has_errors
    assert p.read_bytes()==original

def test_interrupted_replacement_restores_old_and_preserves_inputs(tmp_path,monkeypatch):
    from journeydelta.output import write_reports
    import os
    p=archive(tmp_path,minimal_feed());original=p.read_bytes();out=tmp_path/'out';out.mkdir();(out/'report.json').write_bytes(b'old')
    real=os.replace
    def interrupted(src,dst):
        if '.stage-' in str(src): raise OSError('injected interruption')
        return real(src,dst)
    monkeypatch.setattr('journeydelta.output.os.replace',interrupted)
    r=write_reports({'report.json':b'new'},out,True,(p,))
    assert r.has_errors and p.read_bytes()==original and (out/'report.json').read_bytes()==b'old'

def test_atomic_success(tmp_path):
    from journeydelta.output import write_reports
    out=tmp_path/'out';r=write_reports({'report.json':b'{}','summary.txt':b'hello'},out,False,())
    assert not r.has_errors and (out/'summary.txt').read_bytes()==b'hello'

def test_keyboard_interrupt_restores_previous_output(tmp_path,monkeypatch):
    from journeydelta.output import write_reports
    import os
    out=tmp_path/'out';out.mkdir();(out/'report.json').write_bytes(b'old');real=os.replace
    def interrupted(src,dst):
        if '.stage-' in str(src): raise KeyboardInterrupt()
        return real(src,dst)
    monkeypatch.setattr('journeydelta.output.os.replace',interrupted)
    with pytest.raises(KeyboardInterrupt): write_reports({'report.json':b'new'},out,True,())
    assert (out/'report.json').read_bytes()==b'old'
