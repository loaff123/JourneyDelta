"""Four offline renderers over the same saved result; no feed access."""
import html
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from .report import primitive

def _json(value): return json.dumps(primitive(value),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
def _escape(value): return html.escape(str(value),quote=True)
def _safe_url(value):
    try:
        p=urlsplit(value)
        return p.scheme in ('http','https') and bool(p.hostname) and not p.username and not any(ord(c)<32 for c in value)
    except ValueError: return False

def _text(data):
    lines=[f'JourneyDelta {data["tool_version"]}: {data["status"]}; exit {data["exit_code"]}',data['scope'],f'Canonical digest: {data["canonical_digest"]}']
    for c in data['cases']:
        lines.append(f'{c["id"]}: {c["status"]}')
        if 'comparison' in c:
            r=c['comparison'];lines.append(f'  {r["classification"]}; arrival delta seconds: {r["arrival_delta_seconds"]}')
            for side in ('before','after'):
                direct=r[side];it=direct['itinerary'];lines.append(f'  {side}: {direct["scope"]}')
                if it: lines.append(f'    trip {it["trip_id"]}, service {it["service_date"]}, departure UTC {c["display"][side]["departure"]["utc"]}, arrival UTC {c["display"][side]["arrival"]["utc"]}; wait {it["wait_seconds"]}s, ride {it["ride_seconds"]}s, elapsed {it["elapsed_seconds"]}s')
            lines.append(f'  Assertions: {_json(r["assertions"])}')
    for d in data['diagnostics']:
        lines.append(f'{d["severity"]}: {d["code"]}: {d["message"]}')
        for s in d['sources']: lines.append(f'  {s["side"]}/{s["member_path"]} LF line {s["physical_lf_line"]} bytes [{s["byte_start"]},{s["byte_end"]}) SHA256 {s["member_sha256"]}')
    lines.append('Provenance: '+_json({k:v for k,v in data.items() if k not in ('cases','diagnostics','diagnostic_evidence')}))
    for c in data['cases']:
        if 'evidence' in c: lines.append('Witness evidence '+c['id']+': '+_json(c['evidence']))
    return '\n'.join(lines)+'\n'

def _junit(data):
    cases=data['cases'] or [{'id':'input','status':'error','diagnostics':data['diagnostics']}]
    root=ET.Element('testsuite',name='JourneyDelta scheduled-direct-v0',tests=str(len(cases)),failures=str(sum(c['status']=='fail' for c in cases)),errors=str(sum(c['status']=='error' for c in cases)))
    properties=ET.SubElement(root,'properties')
    ET.SubElement(properties,'property',name='scope',value=data['scope'])
    ET.SubElement(properties,'property',name='canonical_digest',value=data['canonical_digest'])
    ET.SubElement(properties,'property',name='provenance',value=_json({k:v for k,v in data.items() if k not in ('cases','diagnostics','diagnostic_evidence')}))
    for n,d in enumerate(data['diagnostics']): ET.SubElement(properties,'property',name=f'diagnostic.{n}.{d["code"]}',value=_json(d))
    for c in cases:
        node=ET.SubElement(root,'testcase',name=c['id'],classname='scheduled-direct-v0')
        if c['status']=='error': ET.SubElement(node,'error',message='Evaluation blocked').text=_json(c.get('diagnostics',[]))
        elif c['status']=='fail': ET.SubElement(node,'failure',message='Candidate contract violated').text=_json(c['comparison']['assertions'])
        ET.SubElement(node,'system-out').text=_json(c)
    def xml_scalar(text):
        return ''.join(c if ord(c) in (9,10,13) or 0x20<=ord(c)<=0xD7FF or 0xE000<=ord(c)<=0xFFFD or 0x10000<=ord(c)<=0x10FFFF else f'\\u{ord(c):04x}' for c in text)
    for element in root.iter():
        for k,v in element.attrib.items(): element.set(k,xml_scalar(v))
        if element.text: element.text=xml_scalar(element.text)
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def _html(data):
    parts=['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>JourneyDelta report</title>',
           '<style>body{max-width:1100px;margin:2rem auto;padding:0 1rem;font:16px system-ui;color:#17283b;background:#f8fafc}h1,h2{color:#183e62}section,details{background:white;padding:1rem;margin:1rem 0;border:1px solid #d7dfe8;border-radius:.5rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}a{color:#135d9c}li{margin:.4rem 0}</style><body>',
           '<h1>JourneyDelta</h1>',f'<p>{_escape(data["scope"])}</p>',f'<p>Status: {_escape(data["status"])} · Exit {_escape(data["exit_code"])}</p>']
    for side,url in data.get('origin_urls',{}).items():
        if _safe_url(url): parts.append(f'<p><a href="{_escape(url)}" rel="noreferrer">{_escape(side)} origin label</a> (user supplied, not fetched)</p>')
    parts.append('<section><h2>Coverage and model</h2><pre>'+_escape(_json({'coverage':data.get('coverage'), 'timezone':data.get('timezone'),'non_evaluated':data['non_evaluated'],'limits':data['limits']}))+'</pre></section>')
    entries={r['anchor']:r for r in data.get('diagnostic_evidence',[])}
    for c in data['cases']:
        parts.append('<section><h2>'+_escape(c['id'])+' · '+_escape(c['status'])+'</h2><p>'+_escape(c['case'].get('description',''))+'</p>')
        if 'comparison' in c:
            comparison=c['comparison'];parts.append('<p>'+_escape(comparison['classification'])+'; arrival delta seconds: '+_escape(comparison['arrival_delta_seconds'])+'</p>')
            for side in ('before','after'):
                direct=comparison[side];parts.append('<h3>'+side+'</h3><p>'+_escape(direct['scope'])+'</p>')
                if direct['itinerary']:
                    it=direct['itinerary']; view=c['display'][side]
                    parts.append('<p>Trip '+_escape(it['trip_id'])+', service date '+_escape(it['service_date'])+'<br>Departure '+_escape(view['departure']['agency_local'])+' / '+_escape(view['departure']['utc'])+'<br>Arrival '+_escape(view['arrival']['agency_local'])+' / '+_escape(view['arrival']['utc'])+f'<br>Wait {it["wait_seconds"]}s; ride {it["ride_seconds"]}s; elapsed {it["elapsed_seconds"]}s</p>')
            evidence=c['evidence'];parts.append('<p>'+_escape(evidence['causal_claim'])+'</p><ul>')
            for record in evidence['records']:
                entries[record['anchor']]=record;s=record['source']
                parts.append(f'<li><a href="#{record["anchor"]}">{_escape(s["side"])}/{_escape(s["member_path"])} LF line {s["physical_lf_line"]}</a></li>')
            parts.append('</ul>')
        parts.append('<details><summary>Complete case and evidence</summary><pre>'+_escape(_json(c))+'</pre></details></section>')
    parts.append('<section><h2>Diagnostics</h2><pre>'+_escape(_json(data['diagnostics']))+'</pre></section>')
    for anchor,record in sorted(entries.items()):
        parts.append(f'<details id="{anchor}"><summary>{_escape(record["source"]["side"])}/{_escape(record["source"]["member_path"])} LF line {record["source"]["physical_lf_line"]}</summary><pre>'+_escape(_json(record['source']))+'</pre><pre>'+_escape(record['raw_text'])+'</pre></details>')
    parts.append('<details><summary>Input hashes and capability inventory</summary><pre>'+_escape(_json({k:v for k,v in data.items() if k not in ('cases','diagnostics','diagnostic_evidence')}))+'</pre></details><p>Canonical digest: '+_escape(data['canonical_digest'])+'</p></body></html>')
    return ''.join(parts).encode('utf-8')

def render_reports(report):
    data=primitive(report.data)
    return {'report.json':(_json(data)+'\n').encode('utf-8'),'report.html':_html(data),'junit.xml':_junit(data),'summary.txt':_text(data).encode('utf-8')}
