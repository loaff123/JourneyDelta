"""Strict, bounded ZIP/CSV ingestion without extraction or source rewriting."""
import csv
import hashlib
import io
import stat
import struct
import zlib
import zipfile
from pathlib import Path, PurePosixPath
from .models import Diagnostic, Invalid, Limits, Outcome, RawFeed, RawRecord, RawTable, SourceRef, frozen_map

def sha(data):
    return hashlib.sha256(data).hexdigest()

def _csv_fields(text, limits):
    # Python's strict reader still accepts quotes in unquoted fields. Check that
    # grammar explicitly, then use the standard reader for CSV unescaping.
    state = 'start'
    for ch in text:
        if ch in '\r\n\t':
            raise Invalid('invalid_csv', 'Literal CR/LF/tab in CSV field')
        if state == 'start':
            state = 'quoted' if ch == '"' else ('start' if ch == ',' else 'plain')
        elif state == 'plain':
            if ch == '"': raise Invalid('invalid_csv', 'Quote inside unquoted field')
            if ch == ',': state = 'start'
        elif state == 'quoted':
            if ch == '"': state = 'closed'
        else:
            if ch == '"': state = 'quoted'
            elif ch == ',': state = 'start'
            else: raise Invalid('invalid_csv', 'Content after closing quote')
    if state == 'quoted': raise Invalid('invalid_csv', 'Unterminated quoted field')
    # Set to the fixed resource bound rather than the interpreter's 128K default.
    csv.field_size_limit(limits.field_bytes)
    try: fields = next(csv.reader([text], strict=True))
    except csv.Error as exc:
        code = 'resource_limit' if 'field larger' in str(exc) else 'invalid_csv'
        raise Invalid(code, str(exc)) from exc
    if any(len(f.encode('utf-8')) > limits.field_bytes for f in fields):
        raise Invalid('resource_limit', 'CSV field byte limit exceeded')
    return fields

def _table(data, side, name, limits):
    digest = sha(data)
    headers = None
    records = []
    warning_sources = {}
    offset = 0
    chunks = data.split(b'\n')
    if chunks[-1] == b'': chunks.pop()
    for line, chunk in enumerate(chunks, 1):
        terminated = offset + len(chunk) < len(data)
        raw = chunk + (b'\n' if terminated else b'')
        content = chunk
        codes = []
        if terminated and content.endswith(b'\r\r'):
            content = content[:-2]; codes.append('nonstandard_crcrlf')
        elif terminated and content.endswith(b'\r'):
            content = content[:-1]
        if not terminated: codes.append('missing_final_newline')
        if offset == 0 and content.startswith(b'\xef\xbb\xbf'): content = content[3:]
        kind = 'blank' if content == b'' else ('header' if headers is None else 'data')
        ordinal = len(records) + 1 if kind == 'data' else None
        ref = SourceRef(side, name, digest, kind, (str(ordinal),) if ordinal else None,
                        ordinal, line, offset, offset + len(raw))
        offset += len(raw)
        try:
            text = content.decode('utf-8')
            if kind == 'blank':
                codes.append('empty_record')
            else:
                fields = _csv_fields(text, limits)
                if kind == 'header':
                    if any(not h for h in fields) or len(set(fields)) != len(fields):
                        raise Invalid('invalid_header', 'Empty or duplicate CSV header')
                    headers = tuple(fields)
                else:
                    if len(fields) != len(headers): raise Invalid('invalid_csv_width', 'CSV row width differs from header')
                    records.append(RawRecord(frozen_map(zip(headers, fields)), ref))
        except UnicodeDecodeError as exc:
            raise Invalid('invalid_encoding', f'{name}: UTF-8 required', (ref,)) from exc
        except Invalid as exc:
            raise Invalid(exc.diagnostic.code, f'{name}:{line}: {exc}', (ref,)) from exc
        for code in codes: warning_sources.setdefault(code, []).append(ref)
    if headers is None: raise Invalid('invalid_header', f'{name}: CSV header missing')
    warnings = tuple(Diagnostic(c, 'warning', f'{name}: {len(refs)} affected record(s)', tuple(refs))
                     for c, refs in sorted(warning_sources.items()))
    return RawTable(headers, tuple(records), digest), warnings

def _member_bytes(data, z, info, cap):
    # Opening checks overlap, local/central name consistency and ZIP flags;
    # do not let ZipExtFile's declared-size truncation define original bytes.
    with z.open(info):
        pass
    pos = info.header_offset
    if data[pos:pos+4] != b'PK\x03\x04' or pos+30 > len(data):
        raise Invalid('invalid_archive', 'Missing local ZIP header')
    name_len, extra_len = struct.unpack_from('<HH', data, pos+26)
    begin = pos+30+name_len+extra_len
    end = begin+info.compress_size
    if end > len(data): raise Invalid('invalid_archive', 'Truncated compressed member')
    compressed = memoryview(data)[begin:end]
    if info.compress_type == zipfile.ZIP_STORED:
        if len(compressed)>cap: raise Invalid('resource_limit', 'Actual member byte limit exceeded')
        raw=bytes(compressed)
    elif info.compress_type == zipfile.ZIP_DEFLATED:
        decoder=zlib.decompressobj(-15)
        raw=decoder.decompress(compressed,cap+1)
        if len(raw)>cap or decoder.unconsumed_tail:
            raise Invalid('resource_limit', 'Actual decompressed byte limit exceeded')
        if not decoder.eof or decoder.unused_data:
            raise Invalid('invalid_archive', 'Incomplete or trailing compressed stream')
    else:
        raise Invalid('unsupported_compression', 'Only stored and deflated ZIP members are supported')
    if len(raw)!=info.file_size or zlib.crc32(raw)!=info.CRC:
        raise Invalid('invalid_archive', 'Actual member size/CRC differs from ZIP declaration')
    return raw

def read_archive(path: Path, side: str, limits: Limits = Limits()) -> Outcome[RawFeed]:
    warnings = []
    try:
        with Path(path).open('rb') as f: data = f.read(limits.archive_bytes + 1)
        if len(data) > limits.archive_bytes: raise Invalid('resource_limit', 'Archive byte limit exceeded')
        members = {}; tables = {}; excluded = []; total = 0
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            infos = z.infolist()
            if len(infos) > limits.members: raise Invalid('resource_limit', 'Archive member count limit exceeded')
            seen = set()
            for info in infos:
                name = info.filename
                parts = PurePosixPath(name).parts
                if not name or name.startswith('/') or '\\' in name or '..' in parts or ':' in name:
                    raise Invalid('unsafe_archive', f'Unsafe member path: {name!r}')
                if name in seen: raise Invalid('unsafe_archive', f'Duplicate member: {name!r}')
                seen.add(name)
                if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
                    raise Invalid('unsafe_archive', f'Symlink/encrypted member: {name!r}')
                if name.endswith('.txt') and (len(parts) != 1 or '/' in name):
                    raise Invalid('unsafe_archive', f'Nested GTFS table: {name!r}')
                if info.file_size > limits.member_bytes: raise Invalid('resource_limit', 'Member byte limit exceeded')
                raw = _member_bytes(data, z, info, min(limits.member_bytes, limits.total_bytes-total))
                total += len(raw)
                if len(raw) > limits.member_bytes or total > limits.total_bytes:
                    raise Invalid('resource_limit', 'Decompressed byte limit exceeded')
                members[name] = raw
                if name.endswith('.txt'):
                    table, ws = _table(raw, side, name, limits)
                    tables[name] = table; warnings.extend(ws)
                else: excluded.append(name)
        feed = RawFeed(side, data, sha(data), frozen_map(members), frozen_map(tables), tuple(sorted(excluded)), tuple(warnings))
        return Outcome(feed, tuple(warnings))
    except Invalid as exc: return Outcome(None, tuple(warnings) + (exc.diagnostic,))
    except MemoryError:
        return Outcome(None, tuple(warnings) + (Diagnostic('resource_limit', 'error', 'Memory exhausted during ingestion'),))
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, UnicodeError, zlib.error, struct.error) as exc:
        return Outcome(None, tuple(warnings) + (Diagnostic('invalid_archive', 'error', str(exc)),))
