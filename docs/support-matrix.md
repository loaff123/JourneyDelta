# scheduled-direct-v0 support matrix

The normative table/column inventories are `src/journeydelta/data/schema_inventory.json` (scheduled-direct-v0.1) and `vendor_registry.json` (trillium-reviewed-v1), copied byte-for-byte from the reviewed design. Unknown populated fields/tables are unsupported. This is narrower than valid GTFS generally.

| Feature | Treatment |
|---|---|
| One trip instance, repeated platform visits, express overtaking | Evaluated |
| Calendar weekly service and add/remove exceptions | Evaluated on each actual service date |
| Publisher or operator-declared inclusive coverage | Required for the entire common date envelope |
| 00:00:00–71:59:59 clocks, agency timezone, DST | Pinned tzdata; UTC arithmetic from unique local noon |
| Exact frequencies (exact_times=1) | Replaces template, start-inclusive/end-exclusive, strict reference end bound |
| Ordinary boarding/alighting 0/1 | Evaluated |
| Transfers 0–5 and qualifiers/minima | Structural validation and warnings only |
| Parent stations and accessibility declarations | Metadata/inheritance only; exact platform endpoints required |
| Trillium legacy accessibility | Namespaced raw values, never numerically conflated with standard enums |
| Fare, geometry, reviewed vendor labels/link descriptors | Declared metadata, not used for routing; URLs never fetched |
| Unknown all-empty columns | Warning |
| Known empty-only legacy files | Zero records required |
| Unknown table, populated unknown field, pathways, flex/bookings | Blocked |
| Missing event times, non-exact frequencies, contact-based boarding | Blocked |
| Multiple boardings, platform walk, in-seat block continuation, accessibility routing | Unsupported requests |

## Bounds

128 MiB archive; 512 MiB decompressed total; 128 MiB per member; 128 members; 1 MiB UTF-8 field; 100 cases; 250,000 expanded stop events per feed and distinct common horizon/date envelope. Events count before candidate pruning. These are safety bounds, not throughput benchmarks. The suite JSON input additionally has a 4 MiB parsing bound; extremely long integer conversion hits a structured runtime safety-limit diagnostic.

ZIP storage/deflate methods are supported; other compression methods fail explicitly. The parser accepts LF/CRLF, narrowly tolerates CR-CR-LF record boundaries, skips truly empty records, and accepts a complete final record without a terminator. All tolerated issues remain warnings in every report format. No field repair occurs.

## Selection and evidence

Winner tuple: arrival UTC, departure UTC, service date, exact trip ID, generated frequency start (or -1), boarding sequence, alighting sequence. Every witness has one boarding and zero transfers. Source spans are zero-based half-open over original decompressed bytes; physical LF lines and data ordinals are one-based. Header/blank warnings have null keys/ordinals.

A changed old-witness replay is related evidence, not proof of a unique network-wide cause. Identity churn makes replay unavailable without invalidating independently computed results. Deleted records have keyed absence checks and hashes. Diagnostic rows are separate from evaluated itinerary evidence.
