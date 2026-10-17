from dataclasses import dataclass, field
from typing import Generic, TypeVar, Mapping
from types import MappingProxyType

MODEL = 'scheduled-direct-v0'
CLOCK_CAP = 72 * 3600 - 1
FOUND_SCOPE = 'Single boarding only. Multi-leg journeys were not evaluated.'
ABSENT_SCOPE = 'No permitted direct itinerary within this horizon. Multi-leg journeys were not evaluated.'
T = TypeVar('T')

def frozen_map(value):
    return MappingProxyType(dict(value))

@dataclass(frozen=True)
class SourceRef:
    side: str
    member_path: str
    member_sha256: str
    record_kind: str
    logical_key: tuple[str, ...] | None
    data_ordinal: int | None
    physical_lf_line: int
    byte_start: int
    byte_end: int

@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    sources: tuple[SourceRef, ...] = ()

@dataclass(frozen=True)
class Outcome(Generic[T]):
    value: T | None
    diagnostics: tuple[Diagnostic, ...] = ()
    @property
    def has_errors(self):
        return any(d.severity == 'error' for d in self.diagnostics)

class Invalid(Exception):
    def __init__(self, code, message, sources=()):
        self.diagnostic = Diagnostic(code, 'error', message, tuple(sources))
        super().__init__(message)

@dataclass(frozen=True)
class Limits:
    archive_bytes: int = 128 * 1024 * 1024
    total_bytes: int = 512 * 1024 * 1024
    member_bytes: int = 128 * 1024 * 1024
    members: int = 128
    field_bytes: int = 1024 * 1024
    cases: int = 100
    expanded_events: int = 250000

@dataclass(frozen=True)
class RawRecord:
    fields: Mapping[str, str]
    source: SourceRef
    def get(self, name, default=''):
        return self.fields.get(name, default)

@dataclass(frozen=True)
class RawTable:
    headers: tuple[str, ...]
    records: tuple[RawRecord, ...]
    raw_member_sha256: str

@dataclass(frozen=True)
class RawFeed:
    side: str
    archive_bytes: bytes
    archive_sha256: str
    members: Mapping[str, bytes]
    tables: Mapping[str, RawTable]
    excluded_members: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]

@dataclass(frozen=True)
class Horizon:
    start: int
    end: int

@dataclass(frozen=True)
class Coverage:
    start_date: object
    end_date: object
    origin: str = 'operator_declared'
    sources: tuple[SourceRef, ...] = ()

@dataclass(frozen=True)
class Case:
    id: str
    description: str
    origin: str
    destination: str
    horizon: Horizon
    arrive_by: int | None = None
    max_arrival_delay_seconds: int | None = None

@dataclass(frozen=True)
class Suite:
    cases: tuple[Case, ...]
    places: Mapping
    coverage: Mapping
    sha256: str
    origin_urls: Mapping = field(default_factory=lambda: frozen_map({}))

@dataclass(frozen=True)
class ResolvedCase:
    case: Case
    origin_stop: str
    destination_stop: str

@dataclass(frozen=True)
class TypedFeed:
    raw: RawFeed
    tables: Mapping[str, RawTable]
    timezone: str
    inventory: Mapping
    accessibility: Mapping
    diagnostics: tuple[Diagnostic, ...]

@dataclass(frozen=True)
class TzContext:
    zone: str
    zoneinfo: object
    package_version: str
    data_sha256: str

@dataclass(frozen=True)
class Activation:
    service_id: str
    service_date: object
    sources: tuple[SourceRef, ...]

@dataclass(frozen=True)
class Event:
    stop_id: str
    sequence: int
    arrival: int
    departure: int
    pickup: bool
    drop_off: bool
    estimated: bool
    source: SourceRef
    arrival_clock: str
    departure_clock: str

@dataclass(frozen=True)
class Frequency:
    start: int
    end: int
    headway: int
    count: int
    source: SourceRef

@dataclass(frozen=True)
class TripTemplate:
    trip_id: str
    service_id: str
    route_id: str
    events: tuple[Event, ...]
    frequencies: tuple[Frequency, ...]
    source: SourceRef
    wheelchair_accessible: str

@dataclass(frozen=True)
class TripInstance:
    trip_id: str
    service_id: str
    service_date: object
    frequency_start: int | None
    events: tuple[Event, ...]
    sources: tuple[SourceRef, ...]
    wheelchair_accessible: str

@dataclass(frozen=True)
class InstanceWindow:
    instances: tuple[TripInstance, ...]
    horizon: Horizon
    days: tuple
    coverage: Coverage
    tz: TzContext
    expanded_events: int

@dataclass(frozen=True)
class Itinerary:
    trip_id: str
    service_id: str
    service_date: object
    frequency_start: int | None
    departure_utc: int
    arrival_utc: int
    wait_seconds: int
    ride_seconds: int
    elapsed_seconds: int
    board_sequence: int
    alight_sequence: int
    events: tuple[Event, ...]
    sources: tuple[SourceRef, ...]
    estimated: bool
    wheelchair_accessible: str
    boardings: int = 1
    transfers: int = 0

@dataclass(frozen=True)
class DirectResult:
    itinerary: Itinerary | None
    scope: str
    origin_stop: str | None = None
    destination_stop: str | None = None

@dataclass(frozen=True)
class CaseComparison:
    case: Case
    before: DirectResult
    after: DirectResult
    classification: str
    assertions: Mapping[str, str]
    passed: bool
    arrival_delta_seconds: int | None
    existing_deadline_violation: bool

@dataclass(frozen=True)
class EvidenceIndex:
    records: tuple
    absence_checks: tuple
    related_changes: tuple
    replay: Mapping
    causal_claim: str = 'Related witness changes; not a unique network-wide cause.'
