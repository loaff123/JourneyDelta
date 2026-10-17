"""Independent exhaustive direct-pair oracle for tiny test-authored instances."""
def brute_force(window,case):
    choices=[]
    for instance in window.instances:
        for start in instance.events:
            for end in instance.events:
                if start.sequence>=end.sequence: continue
                if start.stop_id!=case.origin_stop or end.stop_id!=case.destination_stop: continue
                if not start.pickup or not end.drop_off: continue
                if start.departure<case.case.horizon.start or end.arrival>case.case.horizon.end: continue
                choices.append((end.arrival,start.departure,instance.service_date,instance.trip_id,instance.frequency_start if instance.frequency_start is not None else -1,start.sequence,end.sequence))
    return min(choices) if choices else None
