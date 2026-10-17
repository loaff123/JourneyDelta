"""Disjoint output validation and staged replacement with rollback."""
import os
import shutil
import tempfile
from pathlib import Path
from .models import Invalid,Outcome

def _check(out,overwrite,input_paths):
    out=Path(out).absolute()
    for p in (out,*out.parents):
        if p.is_symlink(): raise Invalid('output_error',f'Output symlinks are forbidden: {p}')
    resolved=out.resolve()
    for p in input_paths:
        inp=Path(p).resolve()
        if resolved==inp or resolved in inp.parents or inp in resolved.parents:
            raise Invalid('output_error','Inputs and output must be disjoint')
        if out.exists() and Path(p).exists() and os.path.samefile(out,p): raise Invalid('output_error','Output aliases input')
    if out.exists() and not overwrite: raise Invalid('output_error','Output exists; use --overwrite explicitly')
    if not out.parent.is_dir(): raise Invalid('output_error','Output parent directory must already exist')
    return out

def write_reports(files,out,overwrite=False,input_paths=()):
    stage=None;backup=None;target=None
    try:
        target=_check(out,overwrite,input_paths)
        if target.exists() and not target.is_dir(): raise Invalid('output_error','Compare output must be a directory')
        if any(name not in {'report.json','report.html','junit.xml','summary.txt'} for name in files): raise Invalid('output_error','Unexpected report filename')
        stage=Path(tempfile.mkdtemp(prefix='.'+target.name+'.stage-',dir=target.parent))
        for name,data in files.items():
            with (stage/name).open('wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        if target.exists():
            backup=Path(tempfile.mkdtemp(prefix='.'+target.name+'.backup-',dir=target.parent));backup.rmdir();os.replace(target,backup)
        try: os.replace(stage,target);stage=None
        except BaseException:
            if backup is not None: os.replace(backup,target);backup=None
            raise
        if backup is not None: shutil.rmtree(backup);backup=None
        return Outcome(target)
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
    except OSError as exc: return Outcome(None,(Invalid('output_error',f'Output replacement failed: {exc}').diagnostic,))
    finally:
        if stage is not None and stage.exists(): shutil.rmtree(stage)

def write_inspection(data,out,overwrite=False,input_paths=()):
    temp=None
    try:
        target=_check(out,overwrite,input_paths)
        if target.exists() and not target.is_file(): raise Invalid('output_error','Inspect output must be a file')
        fd,name=tempfile.mkstemp(prefix='.'+target.name+'.stage-',dir=target.parent);temp=Path(name)
        with os.fdopen(fd,'wb') as f: f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target);temp=None
        return Outcome(target)
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
    except OSError as exc: return Outcome(None,(Invalid('output_error',str(exc)).diagnostic,))
    finally:
        if temp is not None: temp.unlink(missing_ok=True)
