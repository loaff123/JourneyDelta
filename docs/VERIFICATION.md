# Verification record

Local candidate verification on 17 October 2026. No public repository, push, or public release occurred. The alpha source candidate has local verification only. This report distinguishes completed checks from unavailable coverage.

## Automated checks

- 111 tests passed in the local Python 3.12.14 development environment, including six installed-CLI historical integration tests.
- Clean wheel installs on Python 3.11.17 and Python 3.14.8 each passed all 111 tests with source-path import override disabled (`-o pythonpath=.`). Each historical test invoked that environment's installed CLI.
- Hypothesis profiles are deterministic (`derandomize=True`, no deadline): 150 tiny direct-pair/permutation cases plus 200 varied-bound/dwell/date/frequency cases, with independent exhaustive oracle and witness replay.
- A clean Python 3.13.5 install built from the sdist also passed all 111 tests, including its installed CLI.
- Wheel and sdist builds succeeded using pinned setuptools/build versions. Runtime dependencies are exactly tzdata 2026.5.
- JSON reports were checked with the published Draft 2020-12 schema using verification-only jsonschema 4.26.0. JUnit XML is parsed in tests. Runtime socket creation is blocked in a synthetic comparison test.
- Independent boundary reviews covered ingestion, suite/capabilities, calendars/timezones, instances/frequencies, direct evaluation, evidence, and reports/output. Concrete findings were reproduced and fixed with regression tests. The final whole-project review found four P2 issues and no P1; all four were reproduced, fixed in one pass, and followed by the fresh full-suite runs above. These covered malformed surrogate-key diagnostics, wrong table-error provenance, outer CLI resource failures, and explicit stop remapping in replay.

Commands used for clean installed verification:

```sh
python -m pip install -r requirements-lock.txt dist/journeydelta-0.1.0a1-py3-none-any.whl
JOURNEYDELTA_CALTRAIN_ROOT=/absolute/authorized/fixture-root \
  JOURNEYDELTA_CLI=/absolute/environment/bin/journeydelta python -m pytest -o pythonpath=. -q
```

## Historical Caltrain result

All 56 untouched member hashes match the included source manifest. Deterministic test ZIPs are new containers, not original official archives. Forward late-return comparison restores direct trip 905, service date June 16, departure June 17 08:30Z, arrival 09:30Z, wait 1,800 seconds, ride 3,600 seconds, elapsed 5,400 seconds. Reverse inputs lose direct reachability. Trip 903 is selected by the earlier query. Exact physical LF lines: trip 154, addition exception 2, boarding event 5434, alighting event 5451.

All 261 after/trips.txt CR-CR-LF terminators remain warning locators, including the header. Both type-1 transfer rows remain disclosed and unevaluated. September queries against the baseline's August coverage fail as coverage errors. See the V05 cancellation clarification in data-rights.md.

## Separate Canonical GTFS Validator

Official MobilityData Canonical GTFS Validator **7.1.0**, deliberately pinned and not claimed latest. Artifact and command receipt: [canonical-validator-receipt.json](canonical-validator-receipt.json). Downloaded JAR SHA-256: `52c2785089aaf04e7ba1bb11b2db215692e2622eb0e196b823c194d156d9b58c`. Java 21, one thread, comparison date 2026-06-17, update check disabled (`-svu`). No feed upload.

- Original minimal test-helper fixture: 1 error (`point_near_origin`), 3 warnings. Preserved as a failed attempt, not represented as clean.
- Both shipping synthetic examples (before and delayed after): 0 errors, 0 warnings, 0 info notices each.
- Untouched historical before and after: each 0 errors, 6 warning occurrences, 46 info occurrences; originals unchanged.
- All validator commands exited 0, meaning execution completed. A zero process exit is not a clean-data verdict.
- Optional-data validators skipped: 51 for the synthetic sample, 29 for each historical feed. No system errors. SLF4J emitted a NOP-logger fallback warning.

The source distribution contains notice counts/codes and hashes, not historical source-row samples or raw real-data reports. Full local validation evidence remains outside the candidate artifacts.

## Limits

No claim of all valid GTFS compatibility, live service operation, transfer feasibility, end-to-end accessibility, street routing, realtime correctness, original historical official-ZIP authenticity, legal clearance, benchmark throughput, market demand, adoption, or novel routing science. A valid timetable can still violate a selected local promise.

The CI workflow has not run on GitHub. It declares read-only repository permissions and builds a wheel, then copies tests, schemas, and synthetic examples to a separate temporary directory for installed-package tests and CLI smoke checks. These equivalent commands were exercised locally; hosted CI remains unverified. Historical tests skip explicitly when separately authorized fixture bytes are unavailable. Their local success cannot be inferred from source-only CI. Only the listed interpreter versions and operating environment were actually tested; other platforms have no verification claim.

## Explicit historical fixture opt-in and review boundaries

Historical integration requires an explicit, nonempty `JOURNEYDELTA_CALTRAIN_ROOT` and both `caltrain-before` and `caltrain-after` directories. No adjacent directory is discovered automatically. Five configuration regressions cover unset, empty, missing, before-only, and complete configuration. Three initially failed against the previous behavior; all five passed after the change. With the environment variable unset, the full suite passed 105 tests and explicitly skipped six historical tests even though sibling research data was present.

Legal clearance, package/repository name availability, benchmark performance, and original historical official-ZIP authenticity remain unverified and unclaimed. The checked-in design documents preserve their earlier design-stage status; this verification record describes the implemented local candidate.
