# JourneyDelta

Offline regression tests for named, single-boarding GTFS journeys. Compare two local feed releases and ask whether the candidate still meets a timetable promise.

**Alpha candidate 0.1.0a1.** Single boarding only. Multi-leg journeys were not evaluated. This is neither passenger navigation nor a full GTFS validator. The working package/repository name has not been cleared for public availability. This candidate has local verification only; no public release or hosted CI run has occurred.

## Install and run

Python 3.11 or newer. Runtime dependency: `tzdata==2026.5`; timezone rules never silently come from the host OS.

```sh
python -m pip install .
journeydelta inspect examples/synthetic-before.zip
journeydelta compare examples/synthetic-before.zip examples/synthetic-after.zip \
  --suite examples/journeys.json --out report
```

The supplied original synthetic example deliberately delays arrival by 30 minutes, violating its 08:45 deadline and 5-minute maximum delay. Compare returns **1** and writes:

- `report.json`: versioned result, source spans/hashes, all diagnostics
- `report.html`: self-contained HTML with local evidence links, no JavaScript/assets
- `junit.xml`: CI testcases; blocked cases are errors, never green skips
- `summary.txt`: readable result and provenance

Use `--overwrite` explicitly to replace an output. Inputs must be disjoint from outputs; output symlinks are refused. Reports are staged before replacement. Inspect's optional `--json path` also requires `--overwrite` for an existing file.

## A contract

```json
{
  "schema_version": "1",
  "model": "scheduled-direct-v0",
  "policy": {"accessibility": "unconstrained"},
  "places": {
    "a": {"before_stop_id": "A", "after_stop_id": "A"},
    "b": {"before_stop_id": "B", "after_stop_id": "B"}
  },
  "cases": [{
    "id": "morning_direct",
    "origin": "a",
    "destination": "b",
    "depart_after": "2026-06-17T07:55:00Z",
    "horizon_end": "2026-06-17T09:15:00Z",
    "max_transfers": 0,
    "assertions": {
      "reachable": true,
      "arrive_by": "2026-06-17T08:45:00Z",
      "max_arrival_delay_seconds": 300
    }
  }]
}
```

Whole-second offset-bearing timestamps only. A horizon is at most 48 elapsed hours. Exact platform mappings are mandatory; station endpoints and missing mappings are errors. `arrive_by` asserts the earliest candidate arrival after the query start; it is not a reverse arrive-by search.

When publisher coverage lacks either endpoint, supply both before/after `coverage` intervals using `start_date`/`end_date` in YYYY-MM-DD form. These are disclosed operator assumptions and cannot broaden supplied publisher bounds. Coverage includes the complete common overnight service-date envelope, not merely the query's civil date.

## Supported model

Weekly/exception calendars, supplied stop times through 71:59:59, exact frequencies, ordinary pickup/drop-off permissions, loops/overtaking, stable tie-breaking, and raw source evidence. A later express can beat an earlier local. Service clocks use the agency's local-noon-minus-12-elapsed-hours origin, with pinned timezone bytes.

No transfer/station movement, block chaining, wheelchair routing, realtime, interpolation, flexible service, bookings, or non-exact frequencies. Transfer rows are structurally checked and disclosed; they create no travel edges. Unknown populated fields/tables block evaluation. Known metadata is inventoried. Accessibility declarations remain metadata, with legacy namespaces kept separate.

See [support matrix](docs/support-matrix.md), [data rights](docs/data-rights.md), [third-party notices](docs/third-party-notices.md), [verification](docs/VERIFICATION.md), and [JSON schema](schemas/report-v1.schema.json).

## Exit status

| Code | Meaning |
|---|---|
| 0 | All cases evaluated and passing |
| 1 | Fully evaluated candidate assertion failure, including an existing violation |
| 2 | Invalid/unsupported input, mapping, coverage, or suite |
| 3 | Resource exhaustion, execution, or output failure |

Precedence: 3 > 2 > 1 > 0. Unavailable arrival deltas are null, never infinity or invented zero.

## Reproducibility and safety

No network calls, telemetry, downloader, server, account, or credential handling at runtime. ZIPs are read without extraction. Stored/deflated compression only; actual decompression, stream completion, size, and CRC are checked independently of attacker-supplied uncompressed sizes. All raw archive/member bytes remain unchanged.

The fixed inventories are versioned and hashed. Canonical digests exclude timings. Raw CR-CR-LF record boundaries, empty records, and missing terminal newline are narrowly tolerated with source-located warnings; bare CR, quoted newlines/tabs, malformed quoting, and duplicate headers are errors.

## Development

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-build-isolation -e .
.venv/bin/python -m pytest -q
```

The historical Caltrain fixture bytes are intentionally excluded from this candidate. Local integration tests verify all 56 original member hashes, invoke an independently installed CLI, and run only when `JOURNEYDELTA_CALTRAIN_ROOT` identifies the preserved before/after data directories. No sibling directory is discovered automatically; unset or empty configuration skips the historical tests. Both `caltrain-before` and `caltrain-after` must exist under that root. Set `JOURNEYDELTA_CLI` to that installed executable. Ordinary source-only CI clearly skips these unavailable-data tests; it must not be described as a full real-data pass.

Software is MIT licensed. Third-party fixture data has separate rights and is not covered by the software license. There are no performance, adoption, novelty, live-operation, or original-official-archive authenticity claims.
