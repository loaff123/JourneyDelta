# JourneyDelta Direct-Contract Implementation Plan

> **Testing approach:** Implement one testable step at a time, with focused tests and independent review at each boundary. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the offline scheduled-direct-v0 CLI with one-boarding assertions, paired evidence, and verified overnight Caltrain integration.

**Architecture:** Immutable ZIP/CSV records feed a fixed capability gate, calendar/time/frequency expansion, and a direct-trip occurrence scan. Comparison and evidence are pure transformations; renderers consume one report object. No transfer graph or multi-leg code is included.

**Tech Stack:** Python standard library, pinned tzdata; pytest and Hypothesis for development. Exact tested dependency versions are locked when execution begins.

**Spec:** `docs/superpowers/specs/2026-10-17-journeydelta-design.md`, plus its two normative JSON inventories. Read the real-feed validation addendum and source manifest before handling fixture data.

## Global Constraints

- Python 3.11 or newer.
- Runtime dependencies: pinned tzdata only; standard-library CLI, ZIP, CSV, JSON, HTML/XML, and dataclasses.
- Development dependencies: pytest and Hypothesis; exact tested versions are locked at implementation time.
- The single supported model is scheduled-direct-v0.
- Every accepted case has max_transfers=0 and accessibility="unconstrained".
- Runtime operation is offline; no network requests.
- Unknown populated fields/tables are blocked; no arbitrary ignore list.
- Raw input bytes are never modified.
- Report.json schema_version is "1".
- Timezone data comes from the pinned package, never an implicit host fallback.

Verification approach: use test-driven development, bounded tests at each component boundary, and a final whole-project review. Run aggregate and installed-package checks before preparing a release candidate. This plan does not include public publication.

## Review Focus

- Duplicate JSON object keys and booleans masquerading as integer limits must be rejected, not silently accepted. Owned by Task 2.
- BOMs and CSV boundary normalization must not shift source byte spans or confuse quoted content. Owned by Task 1.
- Missing packaged timezone files must fail even when the host has usable zoneinfo. Owned by Task 3.
- Huge exact-frequency ranges must hit the declared cap before allocating an unbounded expansion. Owned by Task 4.
- Output aliases/symlinks or an interrupted replacement must not overwrite feeds or present a stale success. Owned by Task 7.

## File map and shared types

Create a normal package under `src/journeydelta/`; no files below are product code yet.

| File | Responsibility |
|---|---|
| models.py | Frozen records, typed outcomes, report types, constants |
| archive.py | Safe ZIP bytes, CSV source spans, narrow newline tolerance |
| suite.py | Strict JSON configuration and exact platform mappings |
| capabilities.py | Core validation and fixed schema/extension policies |
| data/schema_inventory.json; data/vendor_registry.json | Copies of reviewed design inventories with version/hash |
| service_time.py; calendars.py | Packaged timezone conversion, dates, coverage, activation evidence |
| frequencies.py; instances.py | Exact templates, date envelope, bounded dated instances |
| direct.py | Single-instance origin/destination search |
| compare.py; evidence.py | Assertions, replay, locators, absence checks |
| report.py; render.py; output.py | Canonical result, four renderers, safe atomic writes |
| app.py; cli.py; __main__.py | Orchestration, inspect/compare entry points |
| tests/support.py; tests/oracle.py | Synthetic builders and independent brute-force oracle |
| tests/fixtures/caltrain/ | Data-only pinned files, notices, hashes, deterministic ZIPs |
| docs/; examples/; .github/workflows/ci.yml | Support matrix, sample cases/reports, CI |

Shared interfaces live in models.py. Use frozen dataclasses and integer UTC seconds:
- `Outcome[T](value: T | None, diagnostics: tuple[Diagnostic, ...])`, with `has_errors`.
- `Diagnostic(code, severity, message, sources: tuple[SourceRef, ...])`; severity is warning/error.
- `SourceRef`: all exact fields and indexing conventions from spec 5.6.
- `Limits`: the exact seven archive/member/field/case/event defaults in spec 9.
- `RawTable.records` is a tuple of `RawRecord`, each with parsed fields and `source: SourceRef`. Test-only `parse_fixture(raw: bytes) -> RawTable` builds an in-memory ZIP through tests/support.py and calls read_archive; it is not a second production parser.
- `RawFeed`: immutable archive/member bytes, hashes, parsed records, source index, diagnostics.
- `TypedFeed`: supported typed tables, source index, capability inventory, diagnostics.
- `Suite, Case, ResolvedCase, Horizon, Coverage, TzContext, Activation, TripTemplate, TripInstance, InstanceWindow, Itinerary, DirectResult, CaseComparison, EvidenceIndex, Report, InspectionReport`: fields follow spec inputs/results. `DirectResult.itinerary` is Itinerary or None; None means evaluated absence only, never an error.
- `Itinerary` exposes trip_id, service_date, departure_utc, arrival_utc, wait_seconds, ride_seconds, elapsed_seconds, boarding/alighting sequences, frequency identity, and sources.
- `Report.exit_code` uses 3 > 2 > 1 > 0 precedence.

Do not introduce a general graph abstraction, transfer-policy module, route planner interface, or future-mode placeholder.

---

### Task 1: Immutable archive and source-record ingestion

**Files:** Create models.py, archive.py, tests/support.py, tests/test_archive.py, pyproject.toml, dependency lock, and package entry-point scaffolding.

**Interfaces:** `read_archive(path: Path, side: str, limits: Limits) -> Outcome[RawFeed]`. SourceRef byte spans are zero-based half-open over original decompressed bytes.

- [ ] Write failing tests for D11–D12/D17, Q14, and raw input preservation. Empty/duplicate CSV headers, including repeated eligibility_restricted columns with values 1,0, must fail before dictionary construction. Pin these exact assertions in tests/test_archive.py:
  `parse_fixture(b"a,b\\r\\r\\n1,2\\r\\r\\n").records[0].source.physical_lf_line == 2`;
  `raw_member_sha256 == sha256(original_bytes).hexdigest()`;
  warnings include nonstandard_crcrlf. Header/blank warnings have null data ordinals with valid raw spans. BOM must add three bytes to the first data span without altering the header key. Bare CR or a quoted newline must error.
- [ ] Run `python -m pytest tests/test_archive.py -q`; verify failure for absent ingestion behavior, not a test syntax error.
- [ ] Implement read_archive plus a strict CSV boundary scanner. Enforce all archive/field limits on actual bytes; normalize only the three spec tolerances in a parse view. Preserve source bytes and record offsets. Add test-only feed/ZIP builders and lock tested dependencies; no runtime network client.
- [ ] Run `python -m pytest tests/test_archive.py -q`; require all ingestion, malicious ZIP, EOF, quote, BOM, and blank-record tests passing.
- [ ] Save tested runtime/development pins in requirements-lock.txt, then commit this boundary locally: `git add pyproject.toml src tests requirements-lock.txt && git commit -m "feat: add immutable GTFS archive ingestion"`.

### Task 2: Strict suite and capability gate

**Files:** Create suite.py, capabilities.py, data/schema_inventory.json, data/vendor_registry.json, tests/test_suite.py, tests/test_capabilities.py.

**Interfaces:** `load_suite(path: Path) -> Outcome[Suite]`; `gate_feed(raw: RawFeed) -> Outcome[TypedFeed]`; `resolve_case(case: Case, suite: Suite, feed: TypedFeed, side: str) -> Outcome[ResolvedCase]`.

- [ ] Write failing tests for D04–D10, D13–D16, Q08/Q12/Q15/Q19. Exact checks: max_transfers=1 errors; min_change_seconds errors; duplicate JSON keys error; max_transfers=false errors; eligibility_restricted="0" passes, "1"/"2" block; a populated new column in route_attributes blocks. The two Caltrain type-1 rows yield transfer_semantics_not_evaluated warnings, not transfer edges.
- [ ] Run `python -m pytest tests/test_suite.py tests/test_capabilities.py -q`; verify meaningful failures.
- [ ] Implement the three interfaces. Copy only the reviewed inventories, hash/version them, validate core keys/enums/hierarchy and direct endpoint scope. Require exact supported model and numeric bounds. Preserve unknown-empty-column and known metadata disclosures. Do not auto-register schemas from input.
- [ ] Run the Task 1–2 tests together; require all assertions, especially restricted/unknown fields and strict JSON parsing, passing.
- [ ] Commit: `git add src/journeydelta tests && git commit -m "feat: enforce direct-only suite and capability contracts"`.

### Task 3: Calendar activation and timezone correctness

**Files:** Create service_time.py, calendars.py, tests/test_service_time.py, tests/test_calendars.py.

**Interfaces:** `load_tz_context(zone: str) -> Outcome[TzContext]`; `service_origin_utc(day: date, tz: TzContext) -> Outcome[int]`; `active_services(feed: TypedFeed, day: date) -> tuple[Activation, ...]`; `resolve_coverage(feed: TypedFeed, supplied: Coverage | None) -> Outcome[Coverage]`.

- [ ] Write failing C01–C08 and T01/T03–T07/T09–T10 tests. Assert New York 2026-03-08 origin 04:00Z, service 02:30→06:30Z; 2026-11-01 origin 05:00Z, service 01:30→06:30Z. Remove packaged timezone access while host zoneinfo exists: must error. Assert duplicate date exceptions fail and suite coverage cannot broaden publisher coverage.
- [ ] Run `python -m pytest tests/test_service_time.py tests/test_calendars.py -q`; verify failures for unimplemented semantics.
- [ ] Implement the interfaces using package resource zoneinfo bytes and ZoneInfo.from_file. Record package version and zone-file SHA-256. Resolve local noon uniquely, then perform arithmetic in UTC. Keep activation and absence evidence separate from coverage.
- [ ] Run the new tests and Tasks 1–2; require exact UTC assertions, package-fallback rejection, and calendar boundary behavior passing.
- [ ] Commit: `git add src/journeydelta tests && git commit -m "feat: add calendar and pinned-timezone semantics"`.

### Task 4: Exact frequencies and bounded dated instances

**Files:** Create frequencies.py, instances.py, tests/test_frequencies.py, tests/test_instances.py.

**Interfaces:** `compile_templates(feed: TypedFeed) -> Outcome[tuple[TripTemplate, ...]]`; `max_expanded_clock(templates: tuple[TripTemplate, ...]) -> int`; `service_dates_for_window(horizon: Horizon, common_max_clock: int, tz: TzContext) -> Outcome[tuple[date, ...]]`; `expand_window(feed: TypedFeed, templates: tuple[TripTemplate, ...], horizon: Horizon, days: tuple[date, ...], coverage: Coverage, tz: TzContext, limits: Limits) -> Outcome[InstanceWindow]`.

- [ ] Write failing R07–R10, C09–C10, T02/T08 tests. Exact start/end/headway 08:00/08:25/600 produces 08:00, 08:10, 08:20, with no template duplicate. A 49:00 event requires earlier service dates. A giant frequency range fails the event cap before creating its full list.
- [ ] Run `python -m pytest tests/test_frequencies.py tests/test_instances.py -q`; verify meaningful failures.
- [ ] Implement integer expansion and the spec's end-bound policy. Compute one common maximum across both feeds in orchestration; enumerate and coverage-check the complete common service-date envelope. Preserve occurrence identity and count events before pruning.
- [ ] Run all tests through Task 4; independently compare compressed and hand-expanded fixtures and assert no silent coverage clipping.
- [ ] Commit: `git add src/journeydelta tests && git commit -m "feat: expand bounded exact timetable instances"`.

### Task 5: Single-boarding evaluator and independent oracle

**Files:** Create direct.py, tests/oracle.py, tests/test_direct.py, tests/test_direct_properties.py.

**Interface:** `choose_direct(window: InstanceWindow, case: ResolvedCase) -> DirectResult`.

- [ ] Write failing D01–D03/D06, R01–R06, Q07/Q10–Q11 tests. Assert an A→P→B two-trip option yields no direct itinerary, while one trip with those stops works. A later express must win over an earlier slower local. Pin the full tie tuple from spec 6.
- [ ] Run `python -m pytest tests/test_direct.py tests/test_direct_properties.py -q`; verify failure before implementation.
- [ ] Implement the single-instance occurrence scan. Separately implement a test oracle using exhaustive origin/destination pairs over test-authored dated instances; do not call production candidate helpers. Add Hypothesis permutations, loops, additions/removals, and one-instance replay properties.
- [ ] Run both files repeatedly with a recorded reproducible Hypothesis profile; require production/oracle agreement and witness invariants. No transfer feasibility tests are claimed.
- [ ] Commit: `git add src/journeydelta/direct.py tests && git commit -m "feat: evaluate direct journeys with independent oracle checks"`.

### Task 6: Assertions and navigable source evidence

**Files:** Create compare.py, evidence.py, tests/test_compare.py, tests/test_evidence.py.

**Interfaces:** `compare_case(before: DirectResult, after: DirectResult, case: Case) -> CaseComparison`; `build_evidence(before: TypedFeed, after: TypedFeed, before_window: InstanceWindow, after_window: InstanceWindow, result: CaseComparison) -> EvidenceIndex`.

- [ ] Write failing Q01–Q06/Q08–Q09/Q16 tests. Pin flagship +1800-second failure and +300-second passing alternative. Before-unreachable/after-reachable has no numeric delta. Reordered rows and tolerated newline variants must resolve correct byte spans; deleted exceptions use explicit absence checks.
- [ ] Run `python -m pytest tests/test_compare.py tests/test_evidence.py -q`; verify failing behavior.
- [ ] Implement assertions and stable-key direct-witness replay. Resolve each locator against raw member bytes; mark replay unavailable on identity churn. Distinguish established outcomes from related evidence and never infer unique causal attribution.
- [ ] Run new tests plus all preceding tests; require exact classifications, deltas, absence evidence, and no unresolved locators.
- [ ] Commit: `git add src/journeydelta tests && git commit -m "feat: compare contracts with source-linked evidence"`.

### Task 7: Reports, CLI, and atomic offline output

**Files:** Create report.py, render.py, output.py, app.py, cli.py, __main__.py, tests/test_reports.py, tests/test_cli.py, tests/test_output.py, schemas/report-v1.schema.json.

**Interfaces:** `run_comparison(before_path: Path, after_path: Path, suite_path: Path, limits: Limits) -> Report`; `run_inspection(feed_path: Path, limits: Limits) -> InspectionReport`; `render_reports(report: Report) -> dict[str, bytes]`; `write_reports(files: dict[str, bytes], out: Path, overwrite: bool, input_paths: tuple[Path, ...]) -> Outcome[Path]`; `main(argv: list[str] | None = None) -> int`.

- [ ] Write failing Q13–Q20 tests plus exact direct-scope copy assertions. Check JSON schema, valid JUnit, warning propagation to all formats, escaped markup, no external resources, error precedence 3>2>1>0, and inspect's coverage-assumption disclosure. Simulate output symlink/alias and failure during staging: inputs stay unchanged and no partial report looks current.
- [ ] Run `python -m pytest tests/test_reports.py tests/test_cli.py tests/test_output.py -q`; verify failures.
- [ ] Implement orchestration and renderers without routing logic. Use standard-library JSON/HTML/XML, explicit HTTP(S) link allowlisting, disjoint input/output validation, temporary staging, and safe atomic replacement. Inspect must not claim canonical validity or run a zero-case comparison.
- [ ] Run all tests with socket creation blocked in runtime tests. Install the package in a clean environment and run both CLI subcommands against synthetic fixtures; require the documented four outputs and exact exit statuses.
- [ ] Commit: `git add src tests schemas && git commit -m "feat: ship offline reports and direct-contract CLI"`.

### Task 8: Real-pair integration and release documentation

**Files:** Create tests/fixtures/caltrain/, tests/test_caltrain_integration.py, examples/, README.md, docs/support-matrix.md, docs/data-rights.md, .github/workflows/ci.yml, and golden report fixtures.

**Consumes:** Installed CLI, all public interfaces, validation/caltrain-source-manifest.json, the 56 inspected data files, and the data-rights discussion.

- [ ] Write failing V01–V07 integration tests. Verify all raw member hashes before building deterministic ZIP containers without changing members. Exact assertion: after trip 905, June 16 service, June 17 departure 08:30Z, arrival 09:30Z, wait=1800, ride=3600, elapsed=5400; before absent; reverse fails. Expect an aggregated CR-CR-LF warning recording 261 occurrences with full locators/count.
- [ ] Run `python -m pytest tests/test_caltrain_integration.py -q`; verify failures before adding fixture wiring.
- [ ] Copy data files only, preserve the source manifest, include separate Caltrain rights/provenance notice, and record newly constructed ZIP hashes without calling them original official archives. Add synthetic mutations as separately labeled fixtures. Document exact exclusions, warnings, coverage, source limitations, and offline commands.
- [ ] Run `python -m pytest -q`, installed CLI integration, oracle/property tests, JSON/JUnit parsing, and static-HTML navigation checks in clean Python 3.11 and the current supported Python release. Run the official Canonical Validator separately on clean synthetic fixtures; record known real-data notices, never hide them. Verify no runtime network access and no fixture/software licensing conflation.
- [ ] Commit locally after independent whole-project review: `git add tests examples docs README.md .github && git commit -m "test: validate real overnight feed change and document limits"`. Record actual commands/results and remaining issues; do not publish.

## Self-review and execution gate

Coverage map: spec 4→Tasks 2/7; 5.1→2; 5.2–5.3→3/4; 5.4→4; 5.5→2/5/6; 5.6→1/6; 6→5/6; 7→6/7; 8–9→1/7; 10 real pair→8; independent checks→3/4/5/6; release definition→8.

All named interfaces are introduced before use. No transfer graph/minimum policy remains. The five review-focus cases have explicit owning tests. The plan is shorter than the specification and includes tests rather than product implementations.

Review this plan and revised spec before execution. No implementation, dependency installation, repository action, or publication has occurred in this design task.

