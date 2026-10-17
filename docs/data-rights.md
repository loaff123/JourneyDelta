# Data rights and provenance

## Original synthetic examples

The synthetic examples were authored for this project and may be redistributed with it. They are fictional timetable data, not travel advice. `synthetic-before.zip` is the separately labeled canonical-clean sample; `synthetic-after.zip` changes the final arrival/departure from 08:30 to 09:00 to demonstrate a failing promise. The original minimal test helper used placeholder coordinates near (0,0), which the Canonical Validator flagged; that failed validator run is retained in the local validation receipt. It is not presented as the clean sample.

## Historical Caltrain pair: bytes excluded

The candidate source archive and wheel do not include Caltrain member bytes, repacked Caltrain archives, generated real-feed reports containing source-row text, validator JARs, or downloaded Python runtimes. No fixture redistribution or publication has been authorized.

A provenance manifest is included at `tests/fixtures/caltrain/source-manifest.json`: 56 exact member sizes, SHA-256 and Git blob hashes, immutable source URLs, repository, path, and commit identifiers. Before commit: `199366246aa54f38e806ba768c9eb1a69736edb2`; after: `6cdd8aa09efc98f9cfae519e3b0118a7941dde7c`. Sources are third-party historical mirrors from davidyen1124/caltrain-mcp, not verified original official historical ZIPs.

Source agency: Peninsula Corridor Joint Powers Board. Publisher: Trillium Solutions, Inc. Relevant data-specific terms: https://www.caltrain.com/developer-resources . Branding is excluded. The design's rights research supports only a qualified data-license reading; it is not legal clearance, a historical-terms audit, or permission to relabel these data under MIT.

Tests build new deterministic ZIP containers from untouched member bytes and record new archive hashes. These are explicitly repacks, not original publisher archives. No raw file is normalized to hide formatting notices. After/trips.txt has 261 CR-CR-LF terminators.

## Cancellation fixture clarification

The sole definition of event service c_71906_b_none_d_0 is its June 16 addition. Deleting that row while retaining trips creates an undefined service reference and correctly yields exit 2. The separately labeled valid cancellation mutation changes the addition to exception_type=2, retaining a defined service; the train disappears and the promise fails with exit 1. This resolves the contradictory original V05 expectation without weakening foreign-key validation. Neither mutation is an untouched historical feed.
