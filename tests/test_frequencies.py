from .support import typed_feed,minimal_feed

def frequency_feed(tmp_path,start='08:00:00',end='08:25:00',headway='600',extra=''):
    d=minimal_feed(); d['frequencies.txt']=f'trip_id,start_time,end_time,headway_secs,exact_times\nt,{start},{end},{headway},1\n{extra}'.encode()
    return typed_feed(tmp_path,d).value

def test_exact_frequency_and_no_template_duplicate(tmp_path):
    from journeydelta.frequencies import compile_templates,occurrence_starts,max_expanded_clock
    r=compile_templates(frequency_feed(tmp_path)); assert not r.has_errors
    assert list(occurrence_starts(r.value[0]))==[28800,29400,30000]
    assert max_expanded_clock(r.value)==31800

def test_adjacent_windows_and_strict_end(tmp_path):
    from journeydelta.frequencies import compile_templates,occurrence_starts
    r=compile_templates(frequency_feed(tmp_path,extra='t,08:25:00,08:40:00,600,1\n'))
    assert list(occurrence_starts(r.value[0]))==[28800,29400,30000,30300,30900]
    assert compile_templates(frequency_feed(tmp_path,end='08:30:00')).has_errors
    assert compile_templates(frequency_feed(tmp_path,extra='t,08:20:00,08:35:00,600,1\n')).has_errors
    assert compile_templates(frequency_feed(tmp_path,start='71:40:00',end='71:55:00')).has_errors

def test_occurrences_carry_frequency_without_rescan(tmp_path):
    from journeydelta.frequencies import compile_templates,occurrences
    t=compile_templates(frequency_feed(tmp_path,extra='t,08:25:00,08:40:00,600,1\n')).value[0]
    pairs=list(occurrences(t))
    assert [p[0] for p in pairs]==[28800,29400,30000,30300,30900]
    assert [p[1].source.logical_key for p in pairs]==[('t','08:00:00')]*3+[('t','08:25:00')]*2
