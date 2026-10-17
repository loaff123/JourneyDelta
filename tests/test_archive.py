import hashlib
import io
import zipfile
import pytest
from .support import archive, parse_fixture

def test_preserves_crcrlf_spans_and_hashes(tmp_path):
    raw = b'a,b\r\r\n1,2\r\r\n'
    result = parse_fixture(tmp_path, raw)
    assert not result.has_errors
    table = result.value.tables['test.txt']
    assert table.records[0].source.physical_lf_line == 2
    assert table.raw_member_sha256 == hashlib.sha256(raw).hexdigest()
    assert table.records[0].source.byte_start == 6
    assert table.records[0].source.byte_end == len(raw)
    warning = next(d for d in result.diagnostics if d.code == 'nonstandard_crcrlf')
    assert len(warning.sources) == 2
    assert warning.sources[0].data_ordinal is None
    assert result.value.members['test.txt'] == raw

@pytest.mark.parametrize('raw', [b'a,a\n1,2\n', b',b\n1,2\n', b'a,b\n1\n', b'a,b\n1,2,3\n', b'a,b\n"bad\nline",2\n', b'a,b\n1\r,2\n', b'a,b\n"1"x,2\n', b'a,b\n1,\t2\n', b'a,b\n"1,2\n', b'a,b\n   \n', b'eligibility_restricted,eligibility_restricted\n1,0\n'])
def test_rejects_malformed_csv(tmp_path, raw):
    assert parse_fixture(tmp_path, raw).has_errors

def test_bom_blank_eof(tmp_path):
    raw=b'\xef\xbb\xbfa,b\n\n"x,y","a""b"'
    result=parse_fixture(tmp_path,raw)
    assert not result.has_errors
    table=result.value.tables['test.txt']
    assert table.headers == ('a','b')
    assert dict(table.records[0].fields)=={'a':'x,y','b':'a"b'}
    assert table.records[0].source.byte_start==8
    assert table.records[0].source.physical_lf_line==3
    assert {'empty_record','missing_final_newline'} <= {d.code for d in result.diagnostics}

@pytest.mark.parametrize('name', ['../stops.txt','/stops.txt','folder/stops.txt','a\\stops.txt'])
def test_unsafe_member(tmp_path,name):
    from journeydelta.archive import read_archive
    from journeydelta.models import Limits
    assert read_archive(archive(tmp_path,{name:b'a\n1\n'}),'before',Limits()).has_errors

def test_duplicate_symlink_and_resource_limits(tmp_path):
    from journeydelta.archive import read_archive
    from journeydelta.models import Limits
    p=tmp_path/'bad.zip'
    with zipfile.ZipFile(p,'w') as z:
        i=zipfile.ZipInfo('stops.txt'); i.create_system=3; i.external_attr=0o120777<<16
        z.writestr(i,b'/etc/passwd')
    assert read_archive(p,'before',Limits()).has_errors
    p=archive(tmp_path,{'a.txt':b'a\n12345\n'})
    result=read_archive(p,'before',Limits(field_bytes=3))
    assert result.has_errors and any(d.code=='resource_limit' for d in result.diagnostics)
    result=read_archive(p,'before',Limits(member_bytes=3))
    assert result.has_errors

def test_raw_records_are_immutable(tmp_path):
    result=parse_fixture(tmp_path,b'a\n1\n')
    with pytest.raises(TypeError): result.value.tables['test.txt'].records[0].fields['a']='2'

@pytest.mark.parametrize('method',[zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED])
def test_actual_decompression_not_forged_header(tmp_path,method):
    import struct,zlib
    from journeydelta.archive import read_archive
    from journeydelta.models import Limits
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=method) as z: z.writestr('a.txt',b'a\n1\n2\n')
    blob=bytearray(out.getvalue()); central=blob.index(b'PK\x01\x02')
    for crc,size in ((14,22),(central+16,central+24)):
        struct.pack_into('<I',blob,crc,zlib.crc32(b'a\n1\n')); struct.pack_into('<I',blob,size,4)
    p=tmp_path/'forged.zip'; p.write_bytes(blob)
    assert read_archive(p,'before',Limits(member_bytes=4,total_bytes=4)).has_errors

def test_invalid_compression_and_filename_return_outcome(tmp_path):
    import struct
    from journeydelta.archive import read_archive
    from journeydelta.models import Limits
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z: z.writestr('a.txt',b'a\n1\n')
    original=out.getvalue(); blob=bytearray(original)
    offset=30+struct.unpack_from('<H',blob,26)[0]+struct.unpack_from('<H',blob,28)[0]; blob[offset]=255
    p=tmp_path/'bad.zip'; p.write_bytes(blob)
    assert read_archive(p,'before',Limits()).has_errors
    blob=bytearray(original); central=blob.index(b'PK\x01\x02')
    struct.pack_into('<H',blob,6,0x800); struct.pack_into('<H',blob,central+8,0x800)
    blob[30]=blob[central+46]=255; p.write_bytes(blob)
    assert read_archive(p,'before',Limits()).has_errors

def test_memory_exhaustion_and_dot_path(tmp_path,monkeypatch):
    from journeydelta.archive import read_archive
    from journeydelta.models import Limits
    p=archive(tmp_path,{'./stops.txt':b'a\n1\n'})
    assert read_archive(p,'before',Limits()).has_errors
    p=archive(tmp_path,{'stops.txt':b'a\n1\n'})
    def exhausted(*args): raise MemoryError()
    monkeypatch.setattr('journeydelta.archive._table',exhausted)
    assert read_archive(p,'before',Limits()).diagnostics[-1].code=='resource_limit'
