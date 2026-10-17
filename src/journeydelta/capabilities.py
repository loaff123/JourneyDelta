"""Fixed inventory gate and direct-model structural validation."""
import hashlib
import json
import re
from dataclasses import replace
from datetime import datetime
from importlib.resources import files
from .models import CLOCK_CAP, Diagnostic, Invalid, Outcome, RawTable, TypedFeed, frozen_map

KEYS={'agency.txt':('agency_id',),'stops.txt':('stop_id',),'routes.txt':('route_id',),'trips.txt':('trip_id',),
      'stop_times.txt':('trip_id','stop_sequence'),'calendar.txt':('service_id',),'calendar_dates.txt':('service_id','date'),
      'frequencies.txt':('trip_id','start_time'),'shapes.txt':('shape_id','shape_pt_sequence'),'levels.txt':('level_id',),'stop_attributes.txt':('stop_id',),'route_attributes.txt':('route_id',),'calendar_attributes.txt':('service_id',)}
REQUIRED={'agency.txt':('agency_name','agency_timezone'),'stops.txt':('stop_id',),'routes.txt':('route_id','route_type'),
          'trips.txt':('route_id','service_id','trip_id'),'stop_times.txt':('trip_id','arrival_time','departure_time','stop_id','stop_sequence'),
          'calendar.txt':('service_id','monday','tuesday','wednesday','thursday','friday','saturday','sunday','start_date','end_date'),
          'calendar_dates.txt':('service_id','date','exception_type'),'frequencies.txt':('trip_id','start_time','end_time','headway_secs','exact_times')}

def date_value(value,source=None):
    refs=(source,) if source else ()
    if not re.fullmatch(r'\d{8}',value): raise Invalid('invalid_date',f'Expected YYYYMMDD: {value!r}',refs)
    try: return datetime.strptime(value,'%Y%m%d').date()
    except ValueError as exc: raise Invalid('invalid_date',f'Invalid date: {value}',refs) from exc

def clock_seconds(value,source=None):
    refs=(source,) if source else ()
    if not re.fullmatch(r'\d{1,2}:\d{2}:\d{2}',value): raise Invalid('invalid_service_time',f'Supplied service clock required: {value!r}',refs)
    h,m,s=map(int,value.split(':'))
    if m>59 or s>59: raise Invalid('invalid_service_time',f'Invalid clock: {value}',refs)
    if h>71: raise Invalid('unsupported_service_clock',f'Clock exceeds 71:59:59: {value}',refs)
    return h*3600+m*60+s

def integer(value,name,minimum=0,source=None):
    refs=(source,) if source else ()
    if not re.fullmatch(r'\d+',value): raise Invalid('invalid_integer',f'{name}: nonnegative integer required',refs)
    try: n=int(value)
    except ValueError as exc: raise Invalid('resource_limit',f'{name}: integer exceeds runtime decimal conversion safety limit',refs) from exc
    if n<minimum: raise Invalid('invalid_integer',f'{name}: minimum {minimum}',refs)
    return n

def _enum(r,k,values,blank=True):
    v=r.get(k)
    if (not v and blank) or v in values: return
    raise Invalid('invalid_enum',f'{k}: invalid value {v!r}',(r.source,))

def gate_feed(raw):
    diagnostics=list(raw.diagnostics)
    try:
        inventories={}
        for name in ('schema_inventory','vendor_registry'):
            data=files('journeydelta').joinpath('data',name+'.json').read_bytes()
            inventories[name]=json.loads(data); inventories[name+'_sha256']=hashlib.sha256(data).hexdigest()
        schema=inventories['schema_inventory']['standard_tables']; vendor=inventories['vendor_registry']
        inventory={}; tables={}
        for name,table in raw.tables.items():
            s=schema.get(name); v=vendor['vendor_tables'].get(name); empty=vendor['empty_only_schemas'].get(name)
            if not any(x is not None for x in (s,v,empty)):
                raise Invalid('unsupported_table',f'Unknown GTFS text table: {name}')
            known=set(sum(s.values(),[]) if s else (v or empty)['columns'])
            known.update(vendor['core_field_extensions'].get(name,{}))
            for column in table.headers:
                nonempty=tuple(r.source for r in table.records if r.get(column)!='')
                if column not in known:
                    if nonempty: raise Invalid('unsupported_column',f'{name}.{column} is populated but unreviewed',nonempty)
                    diagnostics.append(Diagnostic('ignored_empty_column','warning',f'{name}.{column}: ignored empty column'))
                if s and column in s.get('blocked_nonempty',[]) and nonempty:
                    raise Invalid('unsupported_field',f'{name}.{column} is outside scheduled-direct-v0',nonempty)
            if table.records and (empty or (s and s.get('blocked_rows'))):
                raise Invalid('unsupported_table_rows',f'{name}: records are unsupported',tuple(r.source for r in table.records))
            missing=set(REQUIRED.get(name,()))-set(table.headers)
            if missing: raise Invalid('missing_columns',f'{name}: required columns {sorted(missing)}')
            keys=KEYS.get(name); seen=set(); records=[]
            for r in table.records:
                key=tuple(r.get(k) for k in keys) if keys else (str(r.source.data_ordinal),)
                if keys and name!='agency.txt' and any(not v for v in key): raise Invalid('missing_key',f'{name}: empty key', (r.source,))
                # Numeric key components compare numerically; preserve lexical identity in sources.
                unique=tuple((v.lstrip('0') or '0') if k in ('stop_sequence','shape_pt_sequence') and re.fullmatch(r'\d+',v) else v for k,v in zip(keys or (),key)) if keys else key
                if keys and unique in seen: raise Invalid('duplicate_key',f'{name}: duplicate key {key}',(r.source,))
                seen.add(unique)
                records.append(replace(r,source=replace(r.source,logical_key=key)))
            tables[name]=replace(table,records=tuple(records))
            inventory[name]=frozen_map({'rows':len(records),'columns':table.headers,'disposition':'outside_model' if name=='transfers.txt' else 'empty_only' if empty else 'reviewed_vendor_metadata' if v else 'modeled_and_metadata'})
            if v and records: diagnostics.append(Diagnostic('reviewed_metadata','warning',f'{name}: {len(records)} metadata records; no routing effect',tuple(r.source for r in records)))
        for name in ('agency.txt','stops.txt','routes.txt','trips.txt','stop_times.txt'):
            if name not in tables or not tables[name].records: raise Invalid('missing_table',f'Required nonempty table: {name}')
        if not any(n in tables for n in ('calendar.txt','calendar_dates.txt')): raise Invalid('missing_calendar','Calendar representation required')
        rows=lambda n: tables[n].records if n in tables else ()
        index=lambda n,k:{r.get(k):r for r in rows(n)}
        agencies=index('agency.txt','agency_id'); stops=index('stops.txt','stop_id'); routes=index('routes.txt','route_id'); trips=index('trips.txt','trip_id')
        zones={r.get('agency_timezone') for r in agencies.values()}
        if len(zones)!=1 or not next(iter(zones)): raise Invalid('unsupported_timezone','All agencies must use one IANA timezone')
        if len(agencies)>1 and '' in agencies: raise Invalid('missing_key','Multiple agencies need agency_id')
        for r in rows('agency.txt'):
            if not r.get('agency_name'): raise Invalid('missing_value','agency_name is required',(r.source,))
        def ref(r,field,target,required=False):
            val=r.get(field)
            if (required or val) and val not in target: raise Invalid('unresolved_reference',f'{field}: {val!r} missing',(r.source,))
        for r in stops.values():
            _enum(r,'location_type',{'0','1','2','3','4'}); _enum(r,'wheelchair_boarding',{'0','1','2'})
            parent=r.get('parent_station'); kind=r.get('location_type') or '0'
            if parent:
                ref(r,'parent_station',stops)
                pk=stops[parent].get('location_type') or '0'
                if kind=='1' or pk!=('0' if kind=='4' else '1'): raise Invalid('invalid_hierarchy','Invalid parent stop type',(r.source,stops[parent].source))
            elif kind in ('2','3','4'): raise Invalid('invalid_hierarchy','Parent required for entrance/node/boarding area',(r.source,))
            path=set(); current=r.get('stop_id')
            while current:
                if current in path: raise Invalid('invalid_hierarchy','Parent cycle',(r.source,))
                path.add(current)
                if current not in stops: raise Invalid('unresolved_reference',f'Ancestor {current!r} missing',(r.source,))
                current=stops[current].get('parent_station')
        for r in routes.values():
            ref(r,'agency_id',agencies,required=len(agencies)>1)
            _enum(r,'route_type',{str(i) for i in (*range(8),11,12)},False)
            restriction=r.get('eligibility_restricted')
            if restriction in ('1','2'): raise Invalid('unsupported_rider_restriction','Restricted eligibility is unsupported',(r.source,))
            if restriction not in ('','0'): raise Invalid('invalid_enum','Unknown eligibility_restricted value',(r.source,))
            for field in ('continuous_pickup','continuous_drop_off'):
                _enum(r,field,{'0','1','2','3'})
                if r.get(field) not in ('','1'): raise Invalid('unsupported_continuous_service',f'{field} must be unavailable',(r.source,))
        services={r.get('service_id') for n in ('calendar.txt','calendar_dates.txt') for r in rows(n)}
        shapes={r.get('shape_id') for r in rows('shapes.txt')}
        for r in trips.values():
            ref(r,'route_id',routes,True); ref(r,'service_id',services,True); ref(r,'shape_id',shapes)
            _enum(r,'wheelchair_accessible',{'0','1','2'}); _enum(r,'direction_id',{'0','1'}); _enum(r,'bikes_allowed',{'0','1','2'})
        for r in rows('calendar.txt'):
            for day in ('monday','tuesday','wednesday','thursday','friday','saturday','sunday'): _enum(r,day,{'0','1'},False)
            if date_value(r.get('start_date'),r.source)>date_value(r.get('end_date'),r.source): raise Invalid('invalid_date','Reversed calendar dates',(r.source,))
        for r in rows('calendar_dates.txt'):
            date_value(r.get('date'),r.source); _enum(r,'exception_type',{'1','2'},False)
        fi=rows('feed_info.txt')
        if len(fi)>1: raise Invalid('duplicate_key','Only one feed_info record supported')
        for r in fi:
            for field in ('feed_start_date','feed_end_date'):
                if r.get(field): date_value(r.get(field),r.source)
            if r.get('feed_start_date') and r.get('feed_end_date') and r.get('feed_start_date')>r.get('feed_end_date'): raise Invalid('invalid_date','Reversed feed coverage',(r.source,))
        events={t:[] for t in trips}
        for r in rows('stop_times.txt'):
            ref(r,'trip_id',trips,True); ref(r,'stop_id',stops,True)
            if stops[r.get('stop_id')].get('location_type') not in ('','0'): raise Invalid('unsupported_stop_time_location','stop_time must use a platform',(r.source,))
            sequence=integer(r.get('stop_sequence'),'stop_sequence',source=r.source); a=clock_seconds(r.get('arrival_time'),r.source); d=clock_seconds(r.get('departure_time'),r.source)
            if a>d: raise Invalid('invalid_event_order','Arrival is after departure',(r.source,))
            for field in ('pickup_type','drop_off_type'):
                _enum(r,field,{'0','1','2','3'})
                if r.get(field) in ('2','3'): raise Invalid('unsupported_booking',f'{field}: contact-based service unsupported',(r.source,))
            for field in ('continuous_pickup','continuous_drop_off'):
                _enum(r,field,{'0','1','2','3'})
                effective=r.get(field) or routes[trips[r.get('trip_id')].get('route_id')].get(field) or '1'
                if effective!='1': raise Invalid('unsupported_continuous_service',f'{field}: effective value {effective}',(r.source,))
            _enum(r,'timepoint',{'0','1'})
            events[r.get('trip_id')].append((sequence,a,d,r))
        for trip,es in events.items():
            if not es: raise Invalid('missing_stop_times',f'Trip {trip!r} has no stop times',(trips[trip].source,))
            previous=-1
            for seq,a,d,r in sorted(es):
                if a<previous: raise Invalid('invalid_event_order','Backwards trip event time',(r.source,))
                previous=d
        for r in rows('frequencies.txt'):
            ref(r,'trip_id',trips,True); clock_seconds(r.get('start_time'),r.source); clock_seconds(r.get('end_time'),r.source); integer(r.get('headway_secs'),'headway_secs',1,source=r.source)
            _enum(r,'exact_times',{'0','1'})
            if r.get('exact_times')!='1': raise Invalid('unsupported_frequency','Only exact_times=1 is supported',(r.source,))
        for r in rows('transfers.txt'):
            _enum(r,'transfer_type',{str(i) for i in range(6)})
            transfer_type=r.get('transfer_type') or '0'
            for field,target in [('from_stop_id',stops),('to_stop_id',stops),('from_route_id',routes),('to_route_id',routes),('from_trip_id',trips),('to_trip_id',trips)]: ref(r,field,target,(field.endswith('stop_id') and transfer_type not in ('4','5')) or (field.endswith('trip_id') and transfer_type in ('4','5')))
            if r.get('min_transfer_time'): integer(r.get('min_transfer_time'),'min_transfer_time',source=r.source)
            elif r.get('transfer_type')=='2': raise Invalid('missing_transfer_minimum','Type 2 requires min_transfer_time',(r.source,))
        if rows('transfers.txt'):
            ts=rows('transfers.txt'); kinds=sorted({r.get('transfer_type') or '0' for r in ts})
            diagnostics.append(Diagnostic('transfer_semantics_not_evaluated','warning',f'{len(ts)} transfer rows, types {kinds}; not evaluated',tuple(r.source for r in ts)))
        legacy={r.get('stop_id'):r for r in rows('stop_attributes.txt')}
        accessibility={}
        for sid,r in stops.items():
            effective=r.get('wheelchair_boarding') or '0'; refs=[r.source]
            if effective=='0' and r.get('location_type') in ('','0') and r.get('parent_station'):
                parent=stops[r.get('parent_station')]; effective=parent.get('wheelchair_boarding') or '0'; refs.append(parent.source)
            old=legacy.get(sid)
            if old: refs.append(old.source)
            accessibility[sid]=frozen_map({'standard_declared':r.get('wheelchair_boarding') or '0','standard_effective':effective,'legacy_accessibility_id':old.get('accessibility_id') if old else None,'sources':tuple(refs)})
        inventory['versions']=frozen_map({'schema':inventories['schema_inventory']['schema_inventory_version'],'registry':vendor['registry_version'],'schema_sha256':inventories['schema_inventory_sha256'],'registry_sha256':inventories['vendor_registry_sha256']})
        source_index={(r.source.member_path,r.source.byte_start):r.source for table in tables.values() for r in table.records}
        diagnostics=[replace(d,sources=tuple(source_index.get((s.member_path,s.byte_start),s) if s.record_kind=='data' else s for s in d.sources)) for d in diagnostics]
        return Outcome(TypedFeed(raw,frozen_map(tables),next(iter(zones)),frozen_map(inventory),frozen_map(accessibility),tuple(diagnostics)),tuple(diagnostics))
    except Invalid as exc:
        return Outcome(None,tuple(diagnostics)+(exc.diagnostic,))
