from datetime import date,datetime,timezone
import pytest

def test_dst_noon_anchors():
    from journeydelta.service_time import load_tz_context,service_origin_utc
    tz=load_tz_context('America/New_York').value
    for day,expected,clock,result in [(date(2026,3,8),'2026-03-08T04:00:00+00:00',9000,'2026-03-08T06:30:00+00:00'),(date(2026,11,1),'2026-11-01T05:00:00+00:00',5400,'2026-11-01T06:30:00+00:00')]:
        origin=service_origin_utc(day,tz).value
        assert datetime.fromtimestamp(origin,timezone.utc).isoformat()==expected
        assert datetime.fromtimestamp(origin+clock,timezone.utc).isoformat()==result
    assert tz.package_version=='2026.5' and len(tz.data_sha256)==64

def test_missing_package_never_host_fallback(monkeypatch):
    from journeydelta.service_time import load_tz_context
    def unavailable(*args): raise FileNotFoundError('package missing')
    monkeypatch.setattr('journeydelta.service_time.files',unavailable)
    assert load_tz_context('America/New_York').has_errors

def test_offset_instants_are_distinct_and_bad_clocks_rejected():
    from journeydelta.suite import instant
    from journeydelta.capabilities import clock_seconds
    from journeydelta.models import Invalid
    assert instant('2026-11-01T01:30:00-05:00')-instant('2026-11-01T01:30:00-04:00')==3600
    for clock in ('24:60:00','72:00:00','1:2:03'):
        with pytest.raises(Invalid): clock_seconds(clock)
    assert clock_seconds('49:00:00')==176400

def test_missing_and_ambiguous_noon():
    from journeydelta.service_time import load_tz_context,service_origin_utc
    for zone,day in [('Pacific/Apia',date(2011,12,30)),('Pacific/Kwajalein',date(1969,9,30))]:
        r=service_origin_utc(day,load_tz_context(zone).value)
        assert r.has_errors and r.diagnostics[0].code=='unsupported_service_noon'
