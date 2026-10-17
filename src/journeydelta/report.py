import dataclasses
import hashlib
import json
from collections.abc import Mapping
from datetime import date,datetime
from .models import frozen_map


def primitive(value):
    if dataclasses.is_dataclass(value): return {f.name:primitive(getattr(value,f.name)) for f in dataclasses.fields(value)}
    if isinstance(value,Mapping): return {str(k):primitive(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [primitive(v) for v in value]
    if isinstance(value,(date,datetime)): return value.isoformat()
    return value

def canonical_bytes(value):
    return json.dumps(primitive(value),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

@dataclasses.dataclass(frozen=True)
class Report:
    data: Mapping
    @property
    def exit_code(self): return self.data['exit_code']

@dataclasses.dataclass(frozen=True)
class InspectionReport:
    data: Mapping
    @property
    def exit_code(self): return self.data['exit_code']

def _freeze(value):
    if isinstance(value,dict): return frozen_map({k:_freeze(v) for k,v in value.items()})
    if isinstance(value,list): return tuple(_freeze(v) for v in value)
    return value

def finalize(data,inspection=False):
    result=primitive(data)
    result['canonical_digest']=hashlib.sha256(canonical_bytes(result)).hexdigest()
    return (InspectionReport if inspection else Report)(_freeze(result))

def diagnostic_exit(diagnostics):
    errors=[d for d in diagnostics if d.severity=='error']
    return 3 if any(d.code in ('resource_limit','internal_error','output_error') for d in errors) else 2 if errors else 0
