import hashlib
import io
from datetime import datetime, time, timezone
from importlib.resources import files
from importlib.metadata import version, PackageNotFoundError
from zoneinfo import ZoneInfo
from .models import Invalid, Outcome, TzContext

TZDATA_VERSION='2026.5'

def load_tz_context(zone: str) -> Outcome[TzContext]:
    try:
        if not zone or any(p in ('','.', '..') for p in zone.split('/')) or '\\' in zone:
            raise Invalid('unsupported_timezone','Invalid timezone resource name')
        installed=version('tzdata')
        if installed!=TZDATA_VERSION: raise Invalid('timezone_data_mismatch',f'tzdata {TZDATA_VERSION} required, found {installed}')
        data=files('tzdata.zoneinfo').joinpath(*zone.split('/')).read_bytes()
        tz=ZoneInfo.from_file(io.BytesIO(data),key=zone)
        return Outcome(TzContext(zone,tz,installed,hashlib.sha256(data).hexdigest()))
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
    except (OSError,ValueError,ImportError,PackageNotFoundError) as exc:
        return Outcome(None,(Invalid('timezone_data_unavailable',f'Packaged timezone {zone!r}: {exc}').diagnostic,))

def service_origin_utc(day, tz: TzContext) -> Outcome[int]:
    try:
        wall=datetime.combine(day,time(12))
        candidates=set()
        for fold in (0,1):
            local=wall.replace(tzinfo=tz.zoneinfo,fold=fold)
            offset=local.utcoffset()
            if offset is None or abs(offset.total_seconds())>=86400: raise Invalid('unsupported_timezone_offset','Zone offset must be strictly within 24 hours')
            utc=local.astimezone(timezone.utc)
            if utc.astimezone(tz.zoneinfo).replace(tzinfo=None)==wall: candidates.add(int(utc.timestamp()))
        if len(candidates)!=1: raise Invalid('unsupported_service_noon',f'Local noon is missing or nonunique on {day}')
        return Outcome(candidates.pop()-43200)
    except Invalid as exc: return Outcome(None,(exc.diagnostic,))
    except (ValueError,OverflowError) as exc: return Outcome(None,(Invalid('unsupported_date',str(exc)).diagnostic,))

def render_instant(seconds, tz):
    utc=datetime.fromtimestamp(seconds,timezone.utc)
    return {'utc':utc.isoformat().replace('+00:00','Z'),'agency_local':utc.astimezone(tz.zoneinfo).isoformat(),'agency_timezone':tz.zone}
