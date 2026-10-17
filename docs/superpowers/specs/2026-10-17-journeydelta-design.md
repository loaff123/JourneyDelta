# JourneyDelta: single-boarding passenger contracts for GTFS releases

Status: revised design for review; no application has been implemented or published. Revision date: 17 October 2026.

The first release is **scheduled-direct-v0**. Every returned journey boards exactly one trip instance. Multi-leg journeys, transfer feasibility, and cross-trip in-seat continuations are not evaluated. This replaces the earlier multi-transfer proposal following the [real-feed validation](2026-10-17-journeydelta-real-feed-validation.md).

Companion normative inventories:
- [Supported table/field inventory](journeydelta-v0-schema-inventory.json), version scheduled-direct-v0.1
- [Reviewed vendor extension registry](journeydelta-v0-vendor-registry.json), version trillium-reviewed-v1

The working name is not yet cleared for package or repository availability.

## 1. Recommendation and purpose

Build an offline CLI answering: “Does this named direct journey still satisfy our timetable promise?” Two local GTFS archives plus a checked-in JSON suite produce independently evaluated before/after single-boarding itineraries, assertion results, and navigable source evidence.

The audience is a feed maintainer, transit-data integrator, or analyst checking first/last direct service, a holiday schedule, a direct express arrival, or overnight event service. These are proposed use cases, not established customer demand. Reports must disclose the single-boarding restriction wherever a reachability result appears.

**Recommendation: proceed to a plan for this revised scope.** A pinned Caltrain pair has been inspected, and a concrete overnight direct-service change was verified by research calculations. Compatibility depends on the explicit vendor and newline policies below. Product execution and the release acceptance suite remain unverified because the product does not yet exist.

This is a timetable regression-test runner, not passenger navigation, full GTFS validation, a guarantee of operation, or proof of network-wide impact. Its distinction is a small local workflow, named promises, transparent limits, and paired evidence. Do not advertise new routing science or novelty for semantic diffing, source traceability, or before/after passenger analysis.

## 2. Existing tools and bounded differentiation

The following are documented capabilities, not hands-on benchmark results:

| Project | Documented focus | Consequence for JourneyDelta |
|---|---|---|
| [MobilityData Canonical GTFS Schedule Validator](https://github.com/MobilityData/gtfs-validator) | GTFS validation with HTML/JSON notices | Recommend it alongside this tool. A structurally valid feed can still violate a locally chosen journey promise. Do not duplicate its full ruleset. |
| [MobilityData GTFS Diff Engine](https://github.com/MobilityData/gtfs-diff-engine) | File/column/row differences, primary-key evidence, ID-churn and unreliable-diff safeguards | A general row-diff engine is already available. JourneyDelta should inspect relevant witness rows rather than build a competing universal diff format. |
| [niyalist/gtfs-semantic-diff](https://github.com/niyalist/gtfs-semantic-diff) | Human-recognizable change events, content-based ID matching, deterministic reports, and row-to-event traceability | Semantic changes and provenance are established features. Avoid claiming either as unique. Do not add heuristic identity reconciliation to v0. |
| [OpenTripPlanner SpeedTest](https://github.com/opentripplanner/OpenTripPlanner/blob/dev-2.x/test/performance/README.md) | Routing expectations and repeatable performance tests against prepared datasets/graphs | Journey testing is established. JourneyDelta chooses a lighter feed-release CI interface and narrower transit-only model. |
| [Conveyal single-point analysis](https://docs.conveyal.com/analysis) and [regional analysis](https://docs.conveyal.com/analysis/regional) | Scenario comparisons, travel-time distributions, itineraries, and regional accessibility | Do not claim to introduce before/after passenger-impact analysis. Avoid regional accessibility, street-network routing, and stochastic headways in v0. |
| [Transitland diff](https://github.com/interline-io/transitland-lib/blob/main/doc/cli/transitland_diff.md) | GTFS-like feed difference output | Another reason to keep the main interface centered on passenger contracts rather than raw feed changes. |

The proposed combination is: two local archives, a named JSON test suite, mandatory time bounds, explicit model limitations, meaningful CI failure states, paired itineraries, and locally navigable evidence. This is an inference about a useful product shape from the reviewed documentation, not an exhaustive novelty finding. A feature not mentioned in a README may still exist.


## 3. Alternatives and scope decision

1. **Selected: direct-trip evaluator.** Small runtime, easily audited semantics, exact row provenance, and a real overnight validation case. Cost: no connecting-journey promises. This restriction is a product boundary, not an optimization that can be silently lifted.
2. **A complete routing backend such as OpenTripPlanner.** Better fit for transfer/station-access requirements. Its graph building, configuration, provenance integration, and broader semantics need a separate design.
3. **Assertions atop an existing semantic-diff engine.** Useful change context, but a diff alone does not establish a valid scheduled journey. Reuse can be explored without promising a universal feed diff.

Future scope only: multiple boardings, transfer minima, timed-transfer handling, transfer-rule specificity, station traversal, street routing, and accessible paths. None gets a dormant implementation or configuration switch in v0. Requests for them fail explicitly.

## 4. Workflow, inputs, and outputs

Commands:

```text
journeydelta inspect old.zip --json old-capabilities.json
journeydelta compare old.zip new.zip --suite journeys.json --out report/
```

Inspect uses the only supported model, scheduled-direct-v0. It reports “supported with warnings,” “supported,” or precise blockers for that model; it must not report “valid GTFS.” If publisher coverage is incomplete, inspect adds requires_suite_coverage rather than inventing bounds; actual comparison still requires and checks those bounds. Inspect does not run an empty comparison suite. Compare is offline after installation. No downloader, telemetry, server, account, credential, automatic publication, or linked-data fetch is included.

Outputs: versioned report.json, self-contained report.html, junit.xml, and summary.txt. HTML uses ordinary links and disclosure elements without JavaScript or remote assets. Renderers consume one saved result object; they never reopen feeds or recompute an outcome.

### Example suite

```json
{
  "schema_version": "1",
  "model": "scheduled-direct-v0",
  "policy": {"accessibility": "unconstrained"},
  "places": {
    "mountain_view_north": {"before_stop_id": "70211", "after_stop_id": "70211"},
    "san_francisco_north": {"before_stop_id": "70011", "after_stop_id": "70011"}
  },
  "cases": [{
    "id": "event_night_late_return",
    "description": "A direct train home after the event.",
    "origin": "mountain_view_north",
    "destination": "san_francisco_north",
    "depart_after": "2026-06-17T08:00:00Z",
    "horizon_end": "2026-06-17T10:00:00Z",
    "max_transfers": 0,
    "assertions": {
      "reachable": true,
      "arrive_by": "2026-06-17T09:30:00Z"
    }
  }]
}
```

All timestamps are whole-second RFC 3339 instants with explicit offset or Z. An offset-bearing string denotes that instant even when its printed wall time differs from the agency zone. Reject naive local datetimes, fractional seconds, leap seconds, and service-clock strings in query fields. Display agency-zone wall time, its offset, UTC, and service date distinctly.

Each case requires a unique nonempty ID, distinct origin/destination platforms, start < end, max_transfers=0, and assertions.reachable=true. Horizon duration is at most 48 elapsed hours. A nonzero bound is unsupported; an omitted bound is invalid; neither is silently clamped. min_change_seconds is not a v0 suite field and is rejected, rather than falsely appearing to affect direct journeys. Empty suites and assertion objects are errors.

Optional arrive_by is an assertion on earliest arrival after the stated start, not an arrive-by search; it must be inside the closed horizon. Optional max_arrival_delay_seconds is a nonnegative integer. Unknown suite keys are errors. Reject duplicate JSON object member names at every nesting level before constructing mappings; never use first-wins or last-wins interpretation. Booleans are not integers for numeric suite fields. Place aliases explicitly map each feed's exact stop IDs; no name/geographic matching. Missing mapped IDs are mapping errors, not cancellations.

Both releases use the same query instants and policy. No automatic date shifting or representative-weekday selection is permitted. Optional suite coverage is an object with before/after inclusive start_date/end_date intervals, used only under section 5.2.

## 5. Supported semantics and capability boundary

### 5.1 Core records and schema inventories

Required: agency, stops, routes, trips, stop_times, and at least one calendar representation. Multiple agencies are allowed only when they all use one IANA timezone; both releases must use the same agency timezone. Routes resolve to an agency. Identifiers remain exact case-sensitive strings, including leading zeros and spaces; do not silently trim them.

Validate relevant unique keys, core foreign keys, legal modeled enums, dates, increasing stop sequences, arrival <= departure at each event, and nondecreasing event times along a trip. Repeated visits to one stop have separate sequence identities. Every trip must have stop times, and every stop_time must resolve to a trip and a type-0 platform. Reject inconsistent CSV row widths and unresolved referenced parents. For retained metadata, enforce its declared CSV schema; the tool is not a full validator of every non-routing standard constraint.

Every stop-time event supplies arrival and departure. No interpolation. Supplied timepoint=0 estimates are usable but visibly marked. Support service clocks 00:00:00 through 71:59:59, with one- or two-digit hour notation where applicable; minutes/seconds are 00–59. The cap is a tool limit.

Pickup/drop-off 0 or blank permits ordinary boarding/alighting; 1 forbids it. Values 2/3 are unsupported. Passing an intermediate no-pickup/no-drop-off stop while remaining aboard is allowed. A blank route-level continuous_pickup/drop_off defaults to 1 (unavailable); a blank stop-time value inherits the route value. Every effective value must be 1; values 0/2/3 are unsupported. Booking rules used by trips, flexible location references, pickup windows, and populated unmodeled routing fields block the feed.

The two normative JSON inventories enumerate accepted tables and fields. Categories are modeled, metadata, outside_model, blocked_nonempty, blocked_rows, and reviewed empty-only schemas. Unknown populated columns block even within a known table. Unknown all-empty columns produce an ignored_empty_column warning. Unknown GTFS text table names block even when empty. There is no arbitrary ignore list and no “drop unsupported trips” option. Non-GTFS archive attachments are inert, never executed/rendered, and listed as excluded members.

The inventory deliberately supports fewer files than all valid GTFS. For example, unlisted newer fare tables remain unsupported until explicitly reviewed, even though their eventual treatment may be metadata. This prevents a false broad-compatibility claim.

#### Reviewed vendor rules

Registry version trillium-reviewed-v1 is fixed and hashed in every report. Its exact columns are stored in the companion JSON, not inferred from whatever a feed happens to contain.

| Table/field | V0 disposition |
|---|---|
| calendar.service_name; calendar_dates.holiday_name | Display labels only; do not alter dates |
| feed_info.feed_id; feed_license | Identity/rights metadata; never fetched |
| routes.eligibility_restricted | Only blank/0 accepted as unrestricted; 1/2 unsupported; other values invalid |
| calendar_attributes; directions | Labels; no timetable or direction edges |
| farezone_attributes; fare_rider_categories; rider_categories legacy description | Disclosed fare metadata; fares not evaluated |
| realtime_routes; linked_datasets | Disclosed descriptors; no realtime/link request |
| route_attributes | Service/right-of-way classification; no timetable changes |
| stop_attributes | Stop descriptions plus namespaced legacy accessibility declarations |
| Observed areas, booking_rules, location_groups, runcut, timetable_stop_order, timetables legacy schemas | Zero records required; populated versions unsupported |

The [publisher inventory](https://trilliumtransit.com/gtfs/reference/) documents these extensions. The [historical Flex definition](https://github.com/MobilityData/gtfs-flex/blob/2dd3802f6a4219a074153692bebb55625c5d8de6/spec/reference.md#L95-L101) supports interpreting eligibility_restricted=0 as general-public service. Do not classify this field as harmless text.

The registry's MTC source links define route classification and legacy accessibility. accessibility_id=2 has a different meaning from standard wheelchair_boarding=2. Retain its namespace and raw declaration; never convert by matching numeric values.

### 5.2 Calendars, coverage, and exceptions

Compute weekly activation within each calendar row's inclusive bounds, then apply the date exception. Addition activates a service date, including an exception-only service; removal deactivates it. An exceptions-only feed is supported. Duplicate service/date exceptions, even identical duplicates, are invalid. A trip must reference a service defined by a calendar row or an exception row. Cancellation on a civil date must not accidentally cancel an earlier service day's overnight trip. These semantics are based on the [GTFS calendar definitions](https://gtfs.org/documentation/schedule/reference/#calendartxt).

Coverage is separate from the set of active days. Both releases need an explicit interval in which absence of a service record can be interpreted as absence of scheduled service. Use both `feed_start_date` and `feed_end_date` when supplied. Otherwise require the suite's coverage interval as an operator-declared assumption; show its origin prominently. Suite coverage may narrow publisher coverage, but may not broaden or contradict it. A lone publisher endpoint constrains the corresponding supplied endpoint.

The tool must never infer reliable coverage from the first and last active trip. Sparse service dates do not establish what happened between unrelated feed periods. Out-of-coverage queries are blocked rather than counted as lost journeys. Coverage checks are conservative around overnight service and feed boundaries; the report states which service dates are missing. The feed coverage rule is grounded in [feed_info](https://gtfs.org/documentation/schedule/reference/#feed_infotxt).

### 5.3 Service time, dates, timezone, and DST

For service date D, convert D's local noon in the agency timezone to a UTC instant, subtract twelve elapsed hours, then add the parsed service-clock seconds. Perform subtraction/addition in UTC, not by adding a wall-clock timedelta to local midnight. This implements the [GTFS Time definition](https://github.com/google/transit/blob/master/gtfs/spec/en/reference.md#field-types). Preserve service date, original GTFS clock string, UTC instant, and local rendering separately in every event.

All timetable comparisons and durations use integer UTC seconds. Stop timezone is display metadata only and does not shift stop_times. A trip crossing timezone boundaries retains one scheduling clock. Use a pinned packaged timezone database for both releases, record its version and hash, and do not silently substitute the host machine's timezone rules. If the chosen service date's local noon cannot be resolved uniquely, reject that case as unsupported rather than guessing. No leap-second timestamps or fractional seconds in v0.

Do not load only the query's civil date. Compute a common maximum expanded event clock across the two feeds. Enumerate every service date whose interval from service origin through that maximum can intersect the query horizon, including earlier and later civil dates when applicable. Check this complete candidate date envelope against both coverage intervals, then activate each service using its own calendar. Filter actual event instants to the query horizon only after expansion. Dates may not be silently clipped at the feed or query boundary.

A safe finite enumeration procedure is to consider UTC calendar dates from `date(depart_after - common_max_clock) - 1 day` through `date(horizon_end) + 1 day`, construct their service origins, and retain the exact intersecting intervals. The implementation must verify that the loaded zone's offsets are strictly within ±24 hours; otherwise reject this enumeration path. The one-day pads are for offset bounds, not an assumed one-hour DST change.

### 5.4 Frequency entries

Support only `exact_times=1`. Expand first departures as `start_time + k * headway_secs`, with integer k starting at zero and departures strictly before `end_time`. Shift each supplied template event relative to the template's first departure. For v0 frequency templates, require the first arrival to equal the first departure, preventing a negative initial dwell offset. The frequency row replaces the template's ordinary occurrence; do not also run it once as a scheduled trip. Carry template row, frequency row, service date, and generated first-departure seconds in provenance.

Reject intervals with end no later than start, overlapping intervals for the same trip, nonpositive headways, mixed exact/non-exact entries, and any generated event beyond the model clock cap. Also enforce the exact-schedule end bound in the reference: end must be after the last generated departure but strictly before that departure plus one headway. Adjacent intervals are allowed; an endpoint belongs only to the later interval. Blank or zero `exact_times` blocks comparison, even if a deterministic template happens to exist. Do not manufacture a vehicle at the interval start or use half-headway expected waiting for such service. The [GTFS frequency example](https://gtfs.org/documentation/schedule/examples/frequencies/) illustrates why a headway is not an exact departure schedule.


### 5.5 Platforms, hierarchy, transfers, and accessibility

Endpoints are exact platforms: location_type=0 or blank. Reject stations, entrances, generic nodes, and boarding areas as endpoints with available platform alternatives. No implicit access/egress, best-platform selection, or pathway travel. Types 1–4 may be grouping metadata; validate their parent-type relationships and reject cycles. Parent stations support grouping and standard wheelchair metadata inheritance only. They never create travel edges.

Nonempty pathways remains unsupported. Levels and unused entrances without pathways may be retained as metadata. This conservative restriction is intentional; direct scope does not justify dropping unknown access semantics automatically.

**Transfers and minimum times are not evaluated.** Known transfers.txt columns and structurally valid rows may be present, including types 0–5, route/trip qualifiers, and minimum times. Validate IDs, type enums, nonnegative supplied minima, and required type-2 minimum presence; retain every row in a capability inventory. Emit transfer_semantics_not_evaluated with counts, kinds, and source locators. Do not expand station rules, rank qualifiers, apply minima, hold vehicles, infer walks, or chain trips. Additional populated transfer columns outside the fixed inventory still block.

This is safe only because every permitted journey stays on one trip instance. A direct result makes no statement about a possible connecting alternative or operation affected by real-world holding. Same-trip passage through a stop with transfer restrictions remains permitted. block_id is descriptive, never an in-seat continuation.

Only accessibility="unconstrained" is supported. A wheelchair-constrained request fails with unsupported_accessibility_routing. Show standard trip and boarding declarations including unknown values. An unspecified type-0 child's wheelchair_boarding inherits a supplied parent declaration; an explicit child declaration wins. Link both original and inherited evidence. Keep legacy accessibility_id separate. These are metadata, not a verified station or end-to-end accessible path. The [GTFS accessibility guide](https://gtfs.org/getting-started/features/accessibility/) explains the broader feature set.

### 5.6 Exact ingestion tolerance and provenance

Original archive bytes and decompressed member bytes are immutable. Hash them before interpreting text. UTF-8 with an optional initial BOM is accepted; invalid encoding fails. Reject empty or duplicate CSV header names before constructing row mappings; never let a duplicate eligibility_restricted column hide a restriction. Field values may not contain literal CR/LF/tab. Escaped quotes and comma-bearing quoted fields follow CSV rules.

Accepted delimiters are LF and CRLF. The only extra newline tolerance is:
1. CR-CR-LF **outside quotes**, immediately terminating a record: parse it as one boundary and emit nonstandard_crcrlf with affected record locators/count.
2. Truly empty records outside quoted values: skip with empty_record warning. Whitespace-only or delimiter-bearing records are not empty and must pass normal arity checks.
3. A final complete CSV record without a terminal newline: accept with missing_final_newline warning.

Bare CR, CR inside a field, malformed quoting, field-newline content, inconsistent widths, or attempts to recover truncated rows fail. Never repair field contents or infer missing values. The parse view may normalize only the accepted boundary sequences. Preserve the raw source separately.

SourceRef contains feed side, member path, member SHA-256, record_kind (data/header/blank), logical key, 1-based logical data-record ordinal, 1-based physical LF-line number, and a zero-based half-open raw byte span covering that record including its terminator when present. Header and skipped blank records have null logical keys/data ordinals but retain spans and physical lines for warnings. Data evidence requires a data ordinal and resolved key. This avoids confusing the later Caltrain file's CR-CR-LF with two logical trip rows. Its 261 affected terminators include one header plus 260 data records. Every warning remains in JSON, HTML, JUnit properties, and text summary.

These tolerances are compatibility behavior, not a claim of canonical format compliance. Reports say “supported with warnings.” Warnings do not alone fail an otherwise evaluated promise; errors do.

## 6. Direct-journey evaluation and comparison

Every accepted itinerary has exactly one boarding, zero transfers, and one trip instance identified by (service_date, trip_id, generated_frequency_start or null). Search all later destination occurrences for each permitted origin occurrence in that instance. Origin sequence must precede destination sequence. Departure >= query start and arrival <= horizon end, inclusive. All durations use UTC seconds.

Select earliest arrival. Ties use the stable tuple (arrival_utc, departure_utc, service_date, trip_id, frequency_start_or_minus_one, board_sequence, alight_sequence). Row order, archive order, and route enumeration must not affect the winner. There is no preference for fewer boardings because all results have one.

A scan over dated trip instances with a stop-occurrence index is sufficient. No transfer graph, rounds, labels for boarding counts, platform walking edges, or general routing engine is part of v0. Preserve loops and overtaking; never choose merely the earliest departing train. Do not treat separate exact-frequency departures as one instance.

Return first departure, destination arrival, initial wait, on-vehicle duration, elapsed time since query start, intermediate event references, estimate markers, and declared accessibility annotations. Empty results must use the exact wording:

**No permitted direct itinerary within this horizon. Multi-leg journeys were not evaluated.**

A found-result report also states: “Single boarding only. Multi-leg journeys were not evaluated.”

### Assertions

- reachable=true checks that the candidate/after result has a direct itinerary.
- arrive_by checks candidate arrival <= deadline; equality passes.
- max_arrival_delay_seconds checks after_arrival - before_arrival <= threshold when both exist; earlier arrival is improvement.
- Both absent: reachability failure; arrival/delta unavailable, never infinite or zero placeholders.
- Before exists, after absent: lost direct journey; arrival/delta unavailable.
- Before absent, after exists: restored direct reachability; evaluate absolute candidate assertions; delay unavailable.
- A candidate deadline violation already present before is an existing violation, not a new regression.
- ID/route changes are informational unless a supported assertion fails. No heuristic ID reconciliation.

Any candidate assertion violation fails the case, even if pre-existing. A restored case may pass with a delta-unavailable note. Never rewrite baselines or relax thresholds.

Exit codes: 0 all cases evaluated/passing; 1 fully evaluated assertion failure; 2 malformed/unsupported input, mapping, coverage, or suite error; 3 resource limit/internal execution failure. Precedence is 3 > 2 > 1 > 0. Unaffected cases may retain results, but blocked evaluations are JUnit errors, not green skips. Global feed blockers prevent all dependent case judgments.

## 7. Source-linked reports

Include archive/member hashes, suite hash, model/schema/registry/tool versions, timezone package version and data hash, query bounds, coverage origins, full candidate service-date envelope, capability inventory, excluded/non-evaluated semantics, warnings, and active resource limits. Optional origin URLs are user-supplied labels/links, never fetched or used in place of hashes.

Link each witness to stop_times boarding/alighting/intermediate records, stops, trip, route, and calendar/exception evidence. Frequency occurrences additionally link the template and frequency row. Include relevant hierarchy/accessibility sources. Transfer rows appear under capability disclosures, never as evaluated itinerary evidence.

Report selected evidence rather than the entire raw feed. Deleted records use before references plus keyed absence checks in the complete after table. Absence has table identity, lookup key/date, and source hash; it is not a fabricated row. HTML anchors are derived from encoded keys or hashes. Escape all feed/suite text.

Separate established outcomes from related changed records. Replay an old single-trip witness only when stable keys and occurrence identity permit it. A shifted departure, removed service exception, or no-longer-permitted boarding can explain why that option fails. Such replay is not proof of a unique network-wide cause. If IDs changed, mark replay unavailable and rely on independently computed outcomes.

Synthetic flagship:
- Query 07:55–09:15Z, deadline 08:45Z, allowed arrival delay 300 seconds.
- Before direct trip A 08:00 → B 08:30.
- After same trip A 08:00 → B 09:00.
- Required result: +1800 seconds, delay and deadline failures, source-linked arrival change.
- Add another permitted after trip A 08:05 → B 08:35: select it; +300 seconds passes even though the old trip still worsened.
- Add a faster two-trip connection: it is never considered.

The real overnight case in section 10 is a second flagship, with explicit compatibility warnings and historical-data provenance.

## 8. Architecture and project constraints

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

These exact constraints are copied into the implementation plan.

| Unit | Responsibility |
|---|---|
| Archive/CSV reader | Safe immutable bytes, hashes, record spans, narrowly tolerated boundaries |
| Schema/capability gate | Fixed inventories, relevant validation, warning/blocker values |
| Calendar/time engine | Coverage proof, activation, noon-anchor instants, complete date envelope |
| Frequency expander | Exact occurrences with template/frequency provenance |
| Direct evaluator | Single-instance origin/destination occurrence scan and stable winner |
| Contract comparator | Assertions, classifications, numeric deltas |
| Evidence builder | Resolved SourceRefs, absence checks, direct-witness replay |
| Renderers and CLI | Saved result serialization, four outputs, atomic writes, exit status |

Data flow: parse → gate → coverage/date expansion → direct evaluation independently for each side → assertions/evidence → render. Diagnostics are structured values, not ambiguous empty lists.

## 9. Safety, reproducibility, and resources

Reject absolute/traversal paths, symlinks, encrypted members, duplicate member names, nested GTFS paths, malformed encodings, and malformed CSV. Read members without extracting arbitrary filesystem paths. Apply limits to actual decompressed bytes as well as headers.

Defaults: 128 MiB archive, 512 MiB total uncompressed, 128 MiB per member, 128 members, 1 MiB per field, 100 cases, and 250,000 expanded stop events per distinct common horizon/date envelope. Limits are fixed v0 safety bounds, not benchmarks. Count expanded events before candidate pruning; do not discard data to fit a limit. Query/model bound errors are exit 2; applied resource exhaustion is exit 3.

HTML has no remote assets, JavaScript, tracking, or automatic requests. Only validated HTTP(S) origin links are clickable; escape HTML/XML and attributes. Do not render arbitrary attached archive files.

Never overwrite inputs. Refuse an existing compare output directory or inspect JSON output file unless --overwrite is explicit. Stage completed reports separately and replace atomically; on failure, no stale report may be presented as fresh. Inputs and outputs must resolve to disjoint paths. Do not follow output symlinks.

Identical bytes, suite, model/inventory versions, and timezone data yield identical canonical semantic objects. Exclude runtime timings from the canonical digest. Shuffling CSV rows or ZIP timestamps may alter hashes/locators but not itinerary metrics/assertions.

Fixtures carry separate software and data notices. No arbitrary downloaded feed may be shipped merely because it is publicly readable.

## 10. Acceptance criteria

These are required future tests, not tests already passed by a product. Original synthetic feeds must have valid core references and adequate coverage unless deliberately testing an error.

### Calendar and coverage

| ID | Fixture | Required outcome |
|---|---|---|
| C01 | Weekly service starts Monday and ends Friday | Both boundary dates active; Saturday inactive. |
| C02 | Weekday trip removed by a date exception | Trip absent on that date; row evidence identifies the removal. |
| C03 | Saturday service added by exception | Added trip available despite weekly Saturday flag 0. |
| C04 | No calendar.txt, only dates with added service | Only listed dates active; valid dates-only feed supported. |
| C05 | Duplicate `(service_id,date)` rows | Input error, not last-row-wins behavior. |
| C06 | Before coverage ends before the query; after covers it | Coverage error; no “restored service” comparison. |
| C07 | Neither feed_info bounds nor suite coverage supplied | Explicit coverage error; no inferred min/max active-date coverage. |
| C08 | Covered date has no active service in either feed | Evaluated bounded no-direct-itinerary in both; reachability failure and no numeric delay. |
| C09 | Saturday query uses Friday 25:10 event; Saturday service removed | Friday occurrence remains eligible under its Friday calendar. |
| C10 | Required previous service date falls before reliable coverage | Coverage error identifying the missing date, rather than silently losing overnight service. |

### Time and timezone

| ID | Fixture | Required outcome |
|---|---|---|
| T01 | Friday 23:55 departure, 25:10 arrival | Next-civil-day arrival with Friday service identity; 75-minute ride. |
| T02 | A 49:00 occurrence can reach the query | Include the appropriate earlier service date; do not implement only a one-day lookback. |
| T03 | Agency zone differs from stop_timezone | Arrival instants use agency timezone; stop metadata cannot shift the trip. |
| T04 | America/New_York service date 2026-03-08 | Origin is 04:00Z; service 02:30 is 06:30Z / 01:30−05:00; service 03:30 is 07:30Z / 03:30−04:00. |
| T05 | America/New_York service date 2026-11-01 | Origin is 05:00Z; service 00:30 is 05:30Z / 01:30−04:00; service 01:30 is 06:30Z / 01:30−05:00. |
| T06 | Two query timestamps show 01:30 with offsets −04:00 and −05:00 | They are one hour apart and can return different journeys. |
| T07 | Query timestamp has no offset; GTFS time is 24:60:00; or clock exceeds cap | Precise invalid/unsupported error for the relevant field. |
| T08 | Departure equals start; destination arrival equals horizon | Both boundaries accepted; arrival one second later excluded. |
| T09 | Feed order/host timezone changes | Same canonical metrics when packaged timezone data is unchanged. |
| T10 | Releases have different agency timezones, or local noon is nonunique | Unsupported comparison; no silent normalization assumption. |

The four DST event values above were checked independently with Python's UTC/ZoneInfo conversion while preparing this design. That arithmetic check does not validate a JourneyDelta implementation.

### Trips, frequency, and boarding

| ID | Fixture | Required outcome |
|---|---|---|
| R01 | Trip visits A→P→A→B at increasing sequences | Correct later occurrence available; no stop-ID deduplication. |
| R02 | A later express overtakes an earlier local | Earliest destination arrival wins, not first departure or first route. |
| R03 | Pickup forbidden at origin | Trip cannot be boarded there. |
| R04 | Drop-off forbidden at destination | Cannot finish there; remaining onboard through an intermediate no-drop-off stop still works. |
| R05 | Intermediate event has blank time | Unsupported input; no invented interpolation. |
| R06 | Supplied intermediate timepoint=0 values | Use supplied estimates and retain the estimate marker in both itinerary and evidence. |
| R07 | Exact frequency start 08:00, end 08:25, headway 600; template duration 15 min | Departures only 08:00, 08:10, 08:20; arrivals 08:15, 08:25, 08:35; no ordinary template duplicate. |
| R08 | Exact frequency windows 08:00–08:25 and 08:25–08:40, both headway 600 | Departures 08:00, 08:10, 08:20, 08:25, 08:35; exactly one at the shared boundary. An end exactly one headway after the last generated departure fails the reference's strict end-bound check. |
| R09 | Non-exact/blank exact_times or overlapping frequency intervals | Explicit unsupported/invalid diagnostic; no fabricated precise departure. |
| R10 | Frequency shift creates a 72:00 event | Model-limit error before evaluation. |


### Direct-only scope, hierarchy, accessibility, and ingestion

| ID | Fixture | Required outcome |
|---|---|---|
| D01 | Only A→P and P→B on two trips | No direct itinerary, even with abundant connection time. |
| D02 | Two trips share block_id or have type-4 transfer | Never join them into a direct journey. |
| D03 | Same trip A→P→B; transfer type 3 at P | Continuing on the same instance works; transfer warning remains. |
| D04 | Any known transfer type, minimum, or qualifier | Valid rows are inventoried, never applied; malformed IDs/enums/minima still error. |
| D05 | Parent station or entrance used as endpoint | Scope error with platform alternatives; no teleportation. |
| D06 | Two platforms share a parent | No movement between them; only exact endpoint occurrences count. |
| D07 | Wheelchair request | Unsupported error; never relaxed to unconstrained. |
| D08 | Parent wheelchair=1, child=0 then child=2 | First inherits parent; second preserves child negative; legacy accessibility_id remains separate. |
| D09 | Nonempty pathways | Unsupported input. |
| D10 | max_transfers=1, omitted bound, or min_change_seconds supplied | Explicit unsupported/config error; no hidden connecting mode. |
| D11 | CR-CR-LF outside quotes, empty record, final record without newline | Parse identical values with distinct warnings; preserve exact hashes/spans. |
| D12 | Bare CR, quoted CR/LF/tab, malformed quote, whitespace-only bad row | Input error, never broad normalization. |
| D13 | Trillium eligibility_restricted=0 then 1/2/other | First allowed explicitly; restricted values unsupported; unknown invalid. |
| D14 | Known vendor table gains populated new column | Capability error; table allowlist does not hide unknown fields. |
| D15 | Recognized empty-only file gains a record | Unsupported; empty-file support does not imply feature support. |
| D16 | Legacy accessibility_id=2 alongside wheelchair_boarding=1 | Preserve both namespaced declarations; no numeric conflation. |
| D17 | Duplicate/empty CSV header; duplicate JSON key at any depth | Error before mapping: repeated eligibility_restricted values 1,0 cannot hide restriction, and repeated max_transfers cannot shadow a forbidden value. |

### Contracts, evidence, determinism, and safety

| ID | Fixture | Required outcome |
|---|---|---|
| Q01 | Synthetic flagship 08:30→09:00 arrival | +1800 sec; deadline and delta fail; old direct witness replay links changed arrival. |
| Q02 | Add permitted after direct trip arriving 08:35 | Select alternative; exact +300-sec threshold passes. |
| Q03 | Improvement with all trip IDs changed | Improvement; no ID-churn regression; replay may be unavailable. |
| Q04 | Before/after both violate deadline | Existing candidate violation, exit 1. |
| Q05 | Before direct path, after absent | Lost direct reachability; no fabricated infinite delay. |
| Q06 | Before absent, after direct path | Restored; absolute assertions evaluated; delta unavailable. |
| Q07 | Add faster two-trip option than existing direct trip | Winner stays the permitted direct trip. |
| Q08 | Missing mapped after stop ID | Mapping error, not cancellation; explicit valid remapping works. |
| Q09 | Delay equals threshold, then exceeds by one second | Pass, then fail. |
| Q10 | Shuffle rows and change ZIP timestamps | Same metrics/assertions; correct new hashes and locators. |
| Q11 | Equal arrival, repeated stops, zero-duration events | Stable tie-break, strict sequence ordering, finite evaluation. |
| Q12 | Duplicate keys, unresolved references, invalid sequence | Source-located errors, no partial permissive evaluation. |
| Q13 | HTML/XML text and unsafe origin URL | Escaped output; no unsafe link or script execution. |
| Q14 | ZIP traversal, symlink, duplicates, decompression limit | Safe rejection without extraction or partial success. |
| Q15 | Unknown populated table/column; unknown empty column | First two block; empty column warns. |
| Q16 | Passing case plus blocked case | Nonzero error exit; JUnit error, not skipped-green. |
| Q17 | Case/event/archive resource limit | Exit 3; no truncation. Query/model bound violations remain exit 2. |
| Q18 | Reports opened without network | All local evidence navigation works with no requests. |
| Q19 | Empty suite, duplicate ID, start>=end, unknown model/key | Configuration error. |
| Q20 | Hash inputs before/after and simulate output failure | Inputs unchanged; atomic output does not masquerade as completed. |

### Real Caltrain pair: required integration acceptance

Data-only snapshots:
- Before commit 199366246aa54f38e806ba768c9eb1a69736edb2, feed version UTC: 29-Jan-2026 22:42, coverage 2026-01-31–2026-08-31.
- After commit 6cdd8aa09efc98f9cfae519e3b0118a7941dde7c, feed version UTC: 10-Jun-2026 22:25, coverage 2026-01-31–2027-01-31.
- Repository davidyen1124/caltrain-mcp, path src/caltrain_mcp/data/caltrain-ca-us/.
- Exact member bytes/links/hashes: validation/caltrain-source-manifest.json.
- Raw local copies: validation/caltrain-before and validation/caltrain-after.
- Full field inventory and read-only research receipt are alongside them.

The [official Caltrain developer terms](https://www.caltrain.com/developer-resources) support data redistribution subject to a limited/revocable license; branding is excluded. Use a separate notice and provenance manifest, not the software license. These are third-party mirrored historical data; original historical official ZIP equivalence and legal clearance are not established. The [validation addendum](2026-10-17-journeydelta-real-feed-validation.md) records the terms, provenance, original-profile failures, and source links.

| ID | Fixture | Required outcome |
|---|---|---|
| V01 | Entire untouched member contents, repacked deterministically for tests | Direct profile supports with warnings: 2 timed-transfer rows per side, reviewed metadata, and after/trips.txt CR-CR-LF on 261 record terminators; never label canonical-valid. No rows/columns removed. |
| V02 | Example late-return case, Mountain View 70211 → SF 70011, June 17 08:00–10:00Z | Before: no direct itinerary. After: trip 905 on service date June 16; departure 25:30=08:30Z/01:30 PDT, arrival 26:30=09:30Z/02:30 PDT; wait 1800 sec, ride 3600 sec, elapsed 5400 sec; deadline equality passes. |
| V03 | Reverse inputs, same case and deadline | Lost direct reachability; assertion failure; old witness and calendar exception linked. |
| V04 | June 17 07:20–09:00Z query | Before absent; after trip 903 at 07:30–08:30Z from June 16 clocks 24:30–25:30. |
| V05 | Synthetic mutation removes c_71906_b_none_d_0 June 16 addition | Trip 905 unavailable despite retained trips/stop_times rows. Mark fixture as modified. |
| V06 | Query after baseline August 31 coverage | Coverage error, not restored service based on later extension. |
| V07 | Reproduce exact archive/member receipts and source locators | Original file hashes match manifest; trip 905 LF line 154, exception line 2, boarding stop_time line 5434, arrival line 5451; parser warnings cannot renumber these physical LF lines. |

Research already verified all 56 member sizes/blob hashes, core arity/keys/references/monotonic times, and the listed direct candidates by ad hoc CSV enumeration. It did not run JourneyDelta, a full Canonical Validator, transfer routing, or an original-archive authenticity check. Those limits must remain in fixture documentation.

### Independent checks

- A separately written brute-force oracle enumerates every permitted origin/destination occurrence pair within each dated instance on tiny feeds; it must not reuse the production direct scan or its candidate-selection helper.
- Hand-coded calendar truth tables, the DST instants above, and independently calculated UTC conversions check time/date functions without calling their production equivalents.
- Exact-frequency expansion must match an independently hand-expanded feed, including instance identity and template replacement.
- Adding a trip cannot worsen earliest direct arrival; removing one cannot improve it. Adding only a multi-leg alternative cannot alter a direct result.
- For each chosen witness, independently replay service activation, event times, sequence order, board/alight permissions, exactly one instance, and horizon bounds.
- Resolve every SourceRef and absence check against immutable input bytes; validate spans, field values, and raw hashes.
- Property-based permutations and small loops verify stable metrics. No transfer-feasibility oracle is required or claimed for v0.

## 11. Definition of done

Complete only after all acceptance families, independent oracle/properties, and installed-package CLI tests pass in a clean cloud environment; both synthetic and real-pair reports must be understandable without reading code. All V tests must run through the actual installed CLI. A compatible inspection result alone is insufficient.

Ship the support matrix, single-boarding disclosures, fixed schema/extension inventories, sample suite, original synthetic fixture, data-only Caltrain fixture with rights/provenance, golden reports, JSON schema, exit-code guide, and CI example. Run the Canonical Validator separately on clean synthetic fixtures; preserve/report known real-data notices rather than rewriting the raw fixture to hide them.

No numeric performance or adoption claim is established. Measure resource use before selecting any benchmark budget.

Implementation, installs, repository creation, commits, external publication, and desktop work are outside this design task. The companion implementation plan is for later execution after review. A broader multi-leg release requires a fresh design and real-feed validation.

## 12. Sources and research limits

The official schedule reference consulted on 17 October 2026 reports revision 27 April 2026. Record that target revision in a release; review later schema changes explicitly. Primary reference: [GTFS Schedule Reference](https://gtfs.org/documentation/schedule/reference/) and [official source](https://github.com/google/transit/blob/master/gtfs/spec/en/reference.md). Timezone implementation guidance: [Python zoneinfo](https://docs.python.org/3/library/zoneinfo.html).

Competitor links are in section 2; vendor/legacy definitions are in the fixed registry; Caltrain licensing/provenance are in the validation addendum. Research was targeted, not an exhaustive market survey, customer interview, benchmark, or novelty proof.
