# Testing plan

## Offline Spotify candidate tests
- One valid candidate is selected when it has strong episode identity and a verified artist alias.
- Multiple candidates are evaluated; a wrong first result does not prevent a later correct result from being selected.
- Duplicate track IDs from different query variants are deduplicated.
- Exact normalized title and episode-number evidence outrank generic TKKG artist or album matches.
- An unrelated artist is rejected even if the track title is similar.
- An artist whose name merely contains TKKG is rejected unless explicitly registered as a verified alias.
- A verified historical artist alias is accepted.
- Equal-scoring plausible candidates are rejected as ambiguous.
- Empty, malformed, incomplete, and transiently failing Spotify responses produce distinct diagnostics.

## Spotify release-format tests
- A dedicated episode album with a complete ordered split-track sequence is accepted.
- A single-track episode inside a multi-episode compilation selects only that episode track.
- A compilation containing multiple episodes never contributes neighbouring episode tracks to the selected episode's track list.
- A compilation with multiple plausible matches for the requested episode is rejected.
- Track IDs, album IDs, URLs, titles, numbering, order, and available durations are validated.
- No production path assumes a fixed track count or a particular episode number.
- Existing verified newer-release fixtures continue to produce the same ordered track mappings.

## Historical regression fixtures
Use observed provider metadata, not fabricated IDs or inferred track counts, for:
- Episode 1 and 2: historical artist-credit coverage.
- Episode 20: exact numbered three-episode box search and selection of only the requested disc track.
- Episode 37: negative discovery case. Verify that no unrelated recording is accepted when the historic episode is absent from the current Spotify catalogue.
- Episode 53: additional historical catalogue coverage.
- Episode 100: known successful split-track path.

After fixture coverage passes, run live dry-run checks for representative historical episodes. Record the exact Spotify candidate, artist, album, selected track count, YouTube Music result, and stage timings. A diagnostic unresolved result is not counted as a successful end-to-end resolution.

## Range and batching tests
- Inclusive range selects both endpoints.
- Start equal to end selects exactly one episode.
- Start greater than end is rejected.
- A partially supplied range is rejected by workflow preparation.
- Episodes absent from the catalogue are reported clearly.
- Empty target selection is rejected clearly instead of creating an invalid empty matrix.
- Batch partitioning covers every selected episode exactly once, with no duplicates or omissions.
- Aggregation rejects duplicate episode assignments across matrix batches.
- Full catalogue selection of 243 episodes at batch size five creates 49 batches, below GitHub's 256-job matrix limit.
- Batch size and max parallel values are bounded and validated.
- Scheduled latest-first selection remains limited to five missing mappings.

## Parallel workflow and publication tests
- Matrix jobs run with fail-fast disabled and respect the configured maximum parallelism.
- Each batch uses a unique report path and artifact name.
- Matrix jobs do not write canonical catalogue files or push commits.
- A successful complete run downloads and merges all reports in one aggregation job.
- A failed batch or missing report prevents publication.
- An unresolved episode is represented in the report but does not by itself invalidate the batch job.
- Only verified episode mappings are merged.
- Existing verified mappings survive empty, failed, and conflicting new results.
- The aggregation job refreshes main before merging and validates the complete catalogue before writing.
- Dry-run mode leaves the canonical catalogue unchanged.
- Existing verified mappings are preserved even when new results conflict.
- Write mode creates at most one catalogue commit for the complete run.

## Integration and performance checks
- Run the complete offline unittest suite.
- Run Python compilation and catalogue/schema/export validation.
- Validate both workflow syntax and workflow expressions.
- Run a controlled parallel test on a small range, then compare measured duration with the same range processed sequentially.
- Run the full requested range after the controlled test confirms provider stability.
- Report wall-clock runtime from preparation, summed per-episode processing time, batch count, peak configured parallelism, verified count, unresolved count, and any failed batches.
- Confirm the full run completes without a single sequential 15-minute job carrying the entire catalogue.
- Do not claim a speedup or full-catalogue success until measured.
