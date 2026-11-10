# Implementation notes

## Status
Implementation committed to the approved Request 006 branch. Offline and live CI verification is pending. No canonical catalogue data has been changed, and no full catalogue discovery run has been started.

## Investigation findings
- The current Spotify resolver calls `Song.from_search_term()` and receives one selected result.
- The current artist check accepts only the exact normalized name `TKKG`.
- The current first-track title check assumes a split-track naming pattern.
- The current album resolver treats every album as if it contains only one episode.
- The manual GitHub Actions workflow processes all selected episodes sequentially in one 15-minute job.
- The existing workflow already has a workflow-level concurrency group, manual dry-run/write controls, and JSON report upload. These should be preserved and extended rather than replaced.
- The current CLI already accepts repeated `--episode` values, which can be reused by matrix batches.
- The current report format contains per-episode stage timings and verified mappings, which can be aggregated.

## Evidence still required
- Confirm historical Spotify artist aliases and artist IDs from actual candidate metadata.
- Capture real Spotify metadata fixtures for the historical compilation cases.
- Measure per-episode runtimes and provider behaviour before increasing parallelism.
- Confirm whether the existing audio schema can represent compilation-backed episode track selections without an additive field.

## Test results
Not run. This file will be updated only with checks actually performed after implementation approval.
