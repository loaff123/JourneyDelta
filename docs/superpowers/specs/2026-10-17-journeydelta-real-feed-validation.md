# JourneyDelta: real-feed compatibility decision

Research date: 17 October 2026. This is a design-validation addendum. No product implementation, repository creation, or publication occurred.

Subsequent design decision: the single-boarding recommendation was accepted. The [revised main specification](2026-10-17-journeydelta-design.md) and companion implementation plan now define that scope. References below to the original profile and its no-go result are the historical validation finding, not an additional implemented mode.

## Decision

**No-go for the original, unchanged whole-feed gate. Recommend a revised, explicitly single-boarding first release.**

A real, legally accessible Caltrain pair has been inspected in full. It contains a useful overnight service change and is a plausible redistributable test-data source under Caltrain's data-specific terms. It does **not** fit the original `scheduled-platform-v0` gate: both releases have timed transfers, vendor extensions need an explicit inventory, and the later mirror snapshot has a nonstandard line-ending defect. Calling it compatible without those qualifications would be wrong.

The smallest defensible product adjustment is a distinct `scheduled-direct-v0` profile: exactly one vehicle boarding, exact platform endpoints, no transfers or in-seat cross-trip continuation. It may accept the documented metadata extensions and the specifically defined formatting tolerance below. Keep the original connecting-journey profile blocked for these inputs. Do not add a generic “ignore unsupported features” switch or delete inconvenient rows to make a demo pass.

This establishes one concrete use case, not broad feed compatibility or demand from transit agencies. If connecting journeys are indispensable for the first release, the current evidence is a no-go; choose a mature routing backend or obtain a different compatible pair before implementation.

## 1. Exact pair and provenance

These are versioned copies of real Caltrain data in a public third-party repository, **not official agency-hosted historical ZIPs**.

| Item | Before | After |
|---|---|---|
| Repository | davidyen1124/caltrain-mcp | same |
| Full commit | `199366246aa54f38e806ba768c9eb1a69736edb2` | `6cdd8aa09efc98f9cfae519e3b0118a7941dde7c` |
| Mirror commit date | 29 March 2026 | 16 July 2026 |
| Declared feed version | UTC: 29-Jan-2026 22:42 | UTC: 10-Jun-2026 22:25 |
| Declared service coverage | 2026-01-31 through 2026-08-31 | 2026-01-31 through 2027-01-31 |
| Publisher | Trillium Solutions, Inc. | same |
| Agency/timezone | Caltrain / America/Los_Angeles | same |
| Files inspected | 28 | 28 |

Pinned source directories: [before](https://github.com/davidyen1124/caltrain-mcp/tree/199366246aa54f38e806ba768c9eb1a69736edb2/src/caltrain_mcp/data/caltrain-ca-us) and [after](https://github.com/davidyen1124/caltrain-mcp/tree/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us).

The mirror's [fetch script](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/scripts/fetch_gtfs.py) identifies the upstream ZIP as https://data.trilliumtransit.com/gtfs/caltrain-ca-us/caltrain-ca-us.zip and extracts the download. Both snapshots' feed_info files identify the publisher and version. This supports provenance, but is not proof that every mirrored byte equals its original historical ZIP. No such historical ZIP comparison was available.

All 56 downloaded text files were checked against their Git tree byte sizes and Git blob SHA-1 values. SHA-256 values, exact commit URLs, and sizes are saved in `validation/caltrain-source-manifest.json`. The local copies preserve original bytes, including the later malformed line endings. They are not silently cleaned fixtures.

### Data rights

The [official Caltrain Developer License](https://www.caltrain.com/developer-resources) permits using, reproducing, and redistributing PCJPB data. Its grant is limited and revocable; PCJPB retains ownership and disclaims warranties. No public-GitHub or noncommercial-only restriction, exact attribution wording, or license-copying obligation was found in that data-specific grant. Logos, System Map, and associated protected branding are excluded without approval.

Caltrain's [general website terms](https://www.caltrain.com/terms-of-use) are more restrictive about website content. Use the data-specific grant only for the data files; do not copy website assets. The mirror's [software license](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/LICENSE.md) distinguishes the GTFS data from its software. Do not describe the data as MIT/Apache or include mirror application code.

**Conclusion:** data-only fixture redistribution is reasonably supported by the current dedicated license, subject to its terms. This is a qualified reading, not legal clearance or a historical-terms audit. Before any later publication, include a separate data-rights notice, current official license link, source/version/hash manifest, and any transformation record. Exclude the fixtures from the project's software-license claim.

Suggested notice:

> Historical Caltrain GTFS data fixtures. Source agency: Peninsula Corridor Joint Powers Board. Publisher: Trillium Solutions, Inc. Redistribution is subject to Caltrain's Developer License Agreement. These fixtures are for regression testing and are not current travel information.

## 2. What the files actually contain

| Feature | Before | After | Consequence |
|---|---:|---:|---|
| Agencies / routes | 1 / 5 | 1 / 5 | Single timezone, rail routes |
| Trips | 257 | 260 | Three added event trains |
| Stop-time records | 5,414 | 5,468 | All arrival/departure times supplied |
| Calendar / exception records | 2 / 4 | 2 / 25 | Includes exception-only event services |
| Stops | 106 | 106 | 64 platforms, 31 stations, 11 entrances |
| Platforms actually served | 60 | 60 | Every stop_time points to type 0 |
| Maximum service clock | 25:29:00 | 26:30:00 | Overnight arithmetic is necessary |
| Arrival records at/after 24h | 161 | 204 | Not a merely synthetic edge case |
| Frequencies | 0 | 0 | Header present, no frequency service |
| Transfer records | 2 | 2 | Both type 1: unsupported by original model |
| Pathways | Absent | Absent | No pathway approximation needed |
| Wheelchair-accessible trip flag | All 1 | All 1 | Metadata only; no accessible-path claim |

All stop_times have pickup_type=0, drop_off_type=0, timepoint=1, continuous_pickup=1, and continuous_drop_off=1. The latter means continuous service is unavailable, rather than enabled. Booking/window/flexible-location-related columns in the served rows are empty. Blocks are empty. Nonempty stop timezones all equal the agency timezone. Parent references point to station records.

Read-only checks found no duplicate core keys, mismatched row arity, missing trip/route/service/served-stop references, missing event times, backwards trip times, duplicate stop sequences, or invalid referenced parent-station types. These were focused checks, **not** a Canonical GTFS Validator run or proof of full GTFS conformance.

Complete headers, populated-field counts, small value distributions, row counts, and newline statistics are saved in `validation/caltrain-field-inventory.json`. Results and candidate journeys are in `validation/caltrain-inspection-receipt.json`.

## 3. Exact original-gate failures

### A. Genuine unsupported timed transfers

Both releases contain exactly these records in transfers.txt, data rows 1–2:

| from_stop_id | to_stop_id | transfer_type | min_transfer_time |
|---|---|---|---|
| 70261 | 70261 | 1 | empty |
| 70262 | 70262 | 1 | empty |

These are San Jose Diridon northbound and southbound platforms. They are not blank tables or harmless metadata. Type 1 describes timed transfer behavior in the [official reference](https://gtfs.org/documentation/schedule/reference/#transferstxt). The original design intentionally rejects it.

Do not recast these as type 0, invent a minimum, or claim a transfer-capable result after ignoring them. The pair remains unsupported for the original connecting-journey profile.

### B. Populated vendor extensions

The feed contains, among others:

- calendar.service_name; calendar_dates.holiday_name; feed_info.feed_id
- routes.eligibility_restricted=0 on all five routes
- calendar_attributes, directions, farezone_attributes, fare_rider_categories, realtime_routes, route_attributes, and stop_attributes tables
- linked_datasets: one service-alert endpoint descriptor
- additional fare-category fields in rider_categories

The original unknown-nonempty-field/table rule would reject unregistered extensions. Some already fall within its broadly approved metadata categories, but the actual field inventory was not yet enumerated.

The [publisher's field inventory](https://trilliumtransit.com/gtfs/reference/) documents these extensions and distinguishes labels, fare/display metadata, real-time linkage, and legacy Flex fields. Recognizing a name is not permission to ignore its meaning. In particular, eligibility_restricted is a routing restriction, not decorative metadata.

The [historical GTFS-Flex v1 reference](https://github.com/MobilityData/gtfs-flex/blob/2dd3802f6a4219a074153692bebb55625c5d8de6/spec/reference.md) defines eligibility_restricted=0 or blank as open to the general public. A reviewed compatibility profile may explicitly accept 0, while rejecting 1, 2, or unknown values. Do not add a blanket exception for all vendor routing fields.

The inspected route_attributes values are category=1, subcategory=101, running_way=1. The [official MTC/511 specification, Appendix D.1.2](https://511.org/sites/default/files/pdfs/511-SF-Bay-Open-Data-Specification-Transit_1.pdf#page=115) identifies these as interregional/intercity classification and primarily dedicated right-of-way. They can be disclosed as classification metadata for this timetable-only model. stop_attributes.accessibility_id=2 uses a different enum from standard GTFS wheelchair_boarding: the [original MTC GTFS+ v1.7 document](https://www.transitwiki.org/TransitWiki/images/e/e7/GTFS%2B_Additional_Files_Format_Ver_1.7.pdf#page=7) labels it Full ADA. Preserve its namespace and raw declaration; do not equate its numeric 2 with wheelchair_boarding=2 or turn either into an accessible-path guarantee. The document text was readable; PDF screenshot rendering was unavailable.

Header-only areas, booking_rules, location_groups, runcut, timetable_stop_order, and timetables files contain no data records. Their mere existence must not be confused with active flexible or dispatch service.

### C. Nonstandard line endings in the later mirror

After/trips.txt has 261 occurrences of CR-CR-LF, with 522 CR bytes and 261 LF bytes. The [GTFS file requirements](https://gtfs.org/documentation/schedule/reference/#file-requirements) specify CRLF or LF, so this is a formatting defect. Python's CSV reader with universal newline handling reads 260 complete trip records, but permissive parsing is not evidence of conformance.

Preserve and report this defect. Either reject it with a precise diagnostic, or specify a small, deterministic compatibility tolerance: CR-CR-LF outside quoted values is one record terminator plus an empty physical line; skip empty records with a warning and retain original byte offsets/hash for provenance. Never strip arbitrary carriage returns inside field values, repair arity, merge damaged rows, or label the input clean.

This is a separate ingestion decision. A strict canonical-format requirement would leave this pair incompatible even after the routing-profile adjustment.

## 4. Recommended scope amendment

### New first-release profile: scheduled-direct-v0

- A case has exactly one boarding and a single trip_id instance. max_transfers must be 0; a request for a connection fails as unsupported.
- Exact type-0 endpoints only. Station and entrance selectors remain rejected. No implicit platform access, cross-platform walk, trip chaining, or block continuation.
- Retain calendars/exceptions, coverage checks, bounded UTC horizons, prior-service-day enumeration, noon-anchor time conversion, overnight clocks, supplied stop times, ordinary pickup/drop-off restrictions, and accessibility annotations.
- Explicitly inventory transfer rows as **outside this profile's itinerary domain**, not “supported” or “ignored because distant.” Because no valid result can change vehicles, transfer instructions cannot alter its permitted single-trip path. Do not extend this exemption to the original connecting profile.
- Keep nonexact frequencies, missing times, flexible boarding, active booking requirements, nonempty pathways, unsupported rider restrictions, and unknown populated routing fields blocked. This investigation does not justify relaxing those boundaries.
- Use a versioned publisher-extension registry, with exact table/field names and accepted enums. No user-supplied arbitrary ignore list.
- Accept reviewed labels, fare information, route classification, stop descriptive metadata, and real-time linkage as disclosed non-routing information under this profile. Never fetch linked URLs. Accessibility metadata remains descriptive; no wheelchair-route guarantee.
- For the observed vendor tables, use exactly the headers recorded in caltrain-field-inventory.json as the initial reviewed schema. A new populated column in one of these tables is still unknown until reviewed; accepting a table name alone must not suppress field-level gating.
- Empty known optional/extension tables are disclosed as empty, with their observed headers, rather than treated as evidence that the corresponding service is used.
- Adopt the narrowly described blank-record/newline tolerance only if it is included in the parser contract and tests. Otherwise retain an explicit ingestion error for the later snapshot.

This produces a smaller but useful release: first/last direct train, holiday service, lost express train, and overnight service commitments. The report must say “No permitted direct itinerary within this horizon,” not “No route” or “The network is disconnected.”

A general multi-transfer release is deferred. Preserving its original hard gate prevents the Caltrain demonstration from quietly changing the correctness contract.

## 5. Verified named journey and source evidence

### Case: event-night late return

- Origin: Mountain View Caltrain Northbound, stop 70211.
- Destination: San Francisco Caltrain Northbound, stop 70011.
- Query: 17 June 2026 01:00–03:00 America/Los_Angeles.
- Exact UTC bounds: 2026-06-17T08:00:00Z through 2026-06-17T10:00:00Z.
- Profile: single boarding, unconstrained accessibility.
- Both releases declare coverage for the query and relevant earlier service dates.

**Before:** no direct trip departing at/after 01:00 and arriving by 03:00.

**After:** trip 905, service_id c_71906_b_none_d_0, June 16 service day. Mountain View departure 25:30:00 and San Francisco arrival 26:30:00 correspond to June 17 01:30–02:30 PDT, or 08:30–09:30Z. Initial wait is 30 minutes; elapsed time from query start is 90 minutes; on-vehicle time is 60 minutes.

Pinned witnesses:

- [Trip 905](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us/trips.txt#L154)
- [Added service-date exception](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us/calendar_dates.txt#L2)
- [Boarding record](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us/stop_times.txt#L5434)
- [Arrival record](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us/stop_times.txt#L5451)
- [Origin platform](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us/stops.txt#L41) and [destination platform](https://github.com/davidyen1124/caltrain-mcp/blob/6cdd8aa09efc98f9cfae519e3b0118a7941dde7c/src/caltrain_mcp/data/caltrain-ca-us/stops.txt#L5)

An earlier 00:20–02:00 query also changes from no direct itinerary to trip 903 at 00:30–01:30, from service times 24:30–25:30. Three event trips are added overall: 901, 903, and 905. This is an improvement in before→after direction; reversing inputs yields a useful lost-service regression. No claim is made that this was an actual operational disruption.

All direct candidates were enumerated from the raw CSV for service dates June 14–17, using the documented noon-anchor UTC conversion and both releases' exception rules. With the observed maximum 26:30 clock, this covers every service date that could produce a candidate in these horizons. The enumeration is a research calculation, not a tested JourneyDelta implementation.

## 6. Acceptance tests added by this validation

1. Untouched pair with original scheduled-platform-v0 produces capability errors naming both type-1 transfer records. No itinerary verdict is emitted.
2. Revised direct profile, with documented extension/newline handling, evaluates the late-return case exactly as above; it must inspect all input records before reporting support.
3. Reverse inputs and require continued reachability: fail with a lost direct journey and preserve the old trip/service/stop-time witnesses.
4. June 17 calendar day must enumerate June 16 service. Interpreting 25:30 as June 18 or rejecting it as an invalid wall-clock hour fails.
5. Remove the June 16 service-add exception in a synthetic mutation: trip 905 must disappear, even though trips and stop_times still contain it.
6. Changing max_transfers from 0 to 1 under the direct profile is an explicit unsupported request, not silently clamped.
7. The same Caltrain data under a connecting profile remains blocked by type 1; the presence of a direct answer must not bypass that gate.
8. Change eligibility_restricted from 0 to 1, 2, or an unknown value: capability error, including exact route records.
9. Populate a currently empty booking/window/Flex column: capability error. Empty-header acceptance is not a license to ignore future nonempty semantics.
10. Unknown populated extension field/table remains blocked; known metadata is listed with row counts and policy version.
11. Exact input bytes and hashes are retained despite accepted CR-CR-LF tolerance; a warning identifies the file and affected records. CR inside a field, inconsistent row widths, or malformed quoting remains an error.
12. A query after August 31 is not comparable against the baseline coverage. The later feed's extended calendar is not evidence that the earlier feed has no service.
13. Parent-station and entrance IDs fail as endpoints, even when a child platform would yield a journey.
14. Any wheelchair-constrained request fails explicitly. Positive trip/platform declarations cannot become an accessible-station-path result.

These tests augment the original synthetic suite; they do not replace its DST, exact-frequency, minimum-transfer, and safety tests for any future connecting profile.

## 7. Other bounded leads checked

- MobilityData/gtfs-diff official example_1 before/after ZIPs were inspected. The baseline lacks agency.txt; both contain 42 cross-stop type-0 transfers without a minimum; the updated calendar includes a populated unknown coucou column. No repository LICENSE/NOTICE/COPYING was found. It is not a compatible, cleared demonstration pair.
- An old Caltrain ZIP bundled in Transitland was inspected. Its frequency and transfer tables are empty and the core timetable is simple, but it carries vendor extension tables. Only one data version was established, so it does not meet the meaningful-pair requirement.
- Hamilton's official archive and redistribution license were found, but the archive download returned HTTP 403. No archive bytes were inspected and no compatibility claim is made.

This was a bounded search, not a census of GTFS feeds. It supports the conclusion that the original gate is too restrictive for the concrete candidates tested, not that every useful feed is excluded.

## 8. What is established and what remains

Established: accessible pinned data, a reasonable data-specific redistribution basis, exact-byte receipts, complete field inspection, concrete original-model blockers, an overnight direct-service change, and a narrowly scoped amendment.

Not established: untouched compatibility with the original design, full canonical GTFS validity, original official historical-ZIP authenticity, legal clearance, transfer-capable Caltrain routing, DST behavior from this particular case, or successful execution of a product that has not been built.

**Next design action:** revise the written specification to the explicit direct profile and documented ingestion/extension policy before authorizing implementation. If the broader original profile is retained, leave the project at no-go until a compatible real pair is verified.

