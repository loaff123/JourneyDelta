import io
import zipfile
from pathlib import Path

def zip_bytes(members):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(members.items()):
            z.writestr(zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)), data)
    return out.getvalue()

def archive(tmp_path, members, name='feed.zip'):
    p = tmp_path / name
    p.write_bytes(zip_bytes(members))
    return p

def parse_fixture(tmp_path, raw):
    from journeydelta.archive import read_archive
    from journeydelta.models import Limits
    result = read_archive(archive(tmp_path, {'test.txt': raw}), 'before', Limits())
    return result

def minimal_feed(**overrides):
    members={
      'agency.txt':b'agency_id,agency_name,agency_url,agency_timezone\nag,Agency,https://example.org,Etc/UTC\n',
      'stops.txt':b'stop_id,stop_name,stop_lat,stop_lon\nA,Alpha,1,1\nB,Beta,2,2\nP,Mid,1.5,1.5\n',
      'routes.txt':b'route_id,agency_id,route_short_name,route_type\nr,ag,R,2\n',
      'trips.txt':b'route_id,service_id,trip_id\nr,s,t\n',
      'stop_times.txt':b'trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt,08:00:00,08:00:00,A,1\nt,08:30:00,08:30:00,B,2\n',
      'calendar.txt':b'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\ns,1,1,1,1,1,1,1,20260101,20261231\n',
      'feed_info.txt':b'feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date\nAgency,https://example.org,en,20260101,20261231\n'}
    members.update(overrides)
    return {k:v for k,v in members.items() if v is not None}

def base_suite():
    return {'schema_version':'1','model':'scheduled-direct-v0','policy':{'accessibility':'unconstrained'},
            'places':{'a':{'before_stop_id':'A','after_stop_id':'A'},'b':{'before_stop_id':'B','after_stop_id':'B'}},
            'cases':[{'id':'direct','origin':'a','destination':'b','depart_after':'2026-06-17T07:55:00Z',
                      'horizon_end':'2026-06-17T09:15:00Z','max_transfers':0,
                      'assertions':{'reachable':True,'arrive_by':'2026-06-17T08:45:00Z','max_arrival_delay_seconds':300}}]}

def typed_feed(tmp_path,members=None,side='before'):
    from journeydelta.archive import read_archive
    from journeydelta.capabilities import gate_feed
    from journeydelta.models import Limits
    raw=read_archive(archive(tmp_path,members or minimal_feed(),side+'.zip'),side,Limits())
    assert not raw.has_errors, raw.diagnostics
    return gate_feed(raw.value)
