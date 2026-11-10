# Request 006: Robust historical Spotify matching and parallel audio enrichment

## Status
Awaiting approval

## Desired outcome
Resolve historical TKKG episodes whose Spotify metadata is currently rejected or misidentified, and make full-catalogue audio enrichment practical within GitHub Actions time limits.

The workflow must examine multiple Spotify search candidates, recognise verified historical artist credits and release formats, and process independent episode batches concurrently. Only fully verified episode mappings may be merged into the canonical catalogue.

## Context
The manual audio-enrichment run attempted the catalogue sequentially and reached episode 104 before its 15-minute job timeout. Episodes 1 through 99 mostly failed with `Spotify first-track result is not credited to TKKG`. Episodes 20 and 37 instead failed because the single returned search result was unrelated to the requested episode. Episodes 100 through 103 resolved 40 Spotify and 40 YouTube Music track links each.

Current implementation details:
- `scraper/audio_enrichment.py::_save_spotify_metadata()` uses `Song.from_search_term()`, which returns one search result.
- `resolve_spotify_album()` accepts only the exact artist name `TKKG`.
- It requires the first result title to equal one fixed split-track title pattern.
- It assumes the selected Spotify album contains only the requested episode and validates the entire album as one contiguous track sequence.
- `.github/workflows/audio-enrichment.yml` runs the selected episodes sequentially in one job with `timeout-minutes: 15`.

Relevant files:
- `scraper/audio_enrichment.py`
- `tests/test_audio_enrichment.py`
- `.github/workflows/audio-enrichment.yml`
- `schemas/`
- `docs/knowledge/audio-source-catalogue.md`

## Required behaviour

### Spotify discovery
- Search using multiple episode-identity query variants.
- Retrieve and evaluate multiple Spotify candidates instead of trusting the first result.
- Validate candidate identity using episode number, title, artist credit, album context, track title, and available metadata.
- Support legitimate historical TKKG artist credits, including verified aliases such as `TKKG Retro-Archiv`. Do not accept arbitrary artists merely because their names contain the string TKKG.
- Support both split-track episode releases and historical compilation releases where an episode is represented by one track within a multi-episode box.
- For compilation releases, select only the track or tracks that belong to the requested episode. Do not mistake the entire multi-episode compilation tracklist for the episode's tracklist.
- Continue to validate the complete selected episode track sequence, its identity, ordering, track IDs, and album provenance.
- Reject unrelated, incomplete, or ambiguous candidates. Preserve candidate evidence and rejection reasons in reports.
- Do not weaken the existing YouTube Music exact matching and corroboration requirements.

### Parallel catalogue processing
- Add inclusive manual start and end episode inputs so a user can select a range such as 1 through 243 or 100 through 150.
- Partition selected episodes into bounded batches.
- Run batches as a GitHub Actions matrix with a conservative configurable concurrency cap.
- Keep each batch within its own job timeout and upload a separate report artifact.
- Keep the scheduled run small and latest-first.
- Keep manual catalogue writes opt-in.
- Aggregate all completed batch reports in one final job. Only that job may update the canonical catalogue.
- Refresh the latest main branch before merging results. Preserve existing verified mappings and apply only newly verified mappings.
- Do not publish a partial run if a batch crashes or its report is missing. An episode that is simply unresolved is a normal discovery result and must remain visible in the final report.
- Keep dry-run range discovery available without modifying the canonical catalogue.

## Scope
### Included
- Spotify candidate search and ranking in the existing metadata adapter.
- Verified artist alias handling and release-format classification.
- Historical compilation track selection without episode-specific production branches.
- Regression tests and bounded diagnostic reporting.
- Manual inclusive episode-range inputs.
- Dynamic batching and parallel matrix execution in GitHub Actions.
- Unique per-batch artifacts and one safe aggregation/publication job.
- Documentation updates for Spotify discovery, range selection, batching, and publication safeguards.

### Not included
- Downloading or processing audio.
- Changing TKKGTracker or TKKGDownloader.
- Publishing unverified or ambiguous Spotify or YouTube Music candidates.
- Introducing Spotify credentials or private account access.
- Broadening YouTube Music matching thresholds.
- Changing the canonical dataset shape unless implementation proves an explicit release-selection field is required for consumers.

## Constraints
- TKKGData remains the only authoritative owner of shared episode and provider metadata.
- Existing verified mappings must never be overwritten by an unverified or conflicting result.
- All provider calls must remain unauthenticated and respect reasonable rate limits and backoff.
- Keep the existing metadata-only dependency boundary. No FFmpeg or audio downloads.
- Do not hardcode an individual episode, album ID, playlist ID, or track count in production logic.
- Historical episode numbers and titles may appear in regression fixtures.
- A full catalogue range must be split into enough jobs to remain below GitHub's 256-job matrix limit.
- Matrix workers must not write to the canonical catalogue or race to commit shared files.

## Acceptance criteria
- [ ] Spotify lookup evaluates multiple candidates and does not stop at the first unrelated result.
- [ ] Verified historical artist aliases are accepted through explicit, tested identity rules.
- [ ] Arbitrary artists and weak title-only matches remain rejected.
- [ ] Both split-track albums and single-episode tracks inside compilation albums can be represented correctly.
- [ ] A compilation's unrelated episode tracks are not included in the selected episode's Spotify or YouTube Music track pairing.
- [ ] Ambiguous candidates remain unresolved and include useful diagnostics.
- [ ] Regression fixtures cover episodes 1, 2, 20, 37, 53, and 100, with additional live checks for representative historical episodes.
- [ ] The existing newer release path continues to resolve all its tracks.
- [ ] Manual workflow dispatch supports inclusive start and end episode numbers.
- [ ] The workflow partitions selected episodes into bounded batches and runs multiple batches concurrently.
- [ ] A full catalogue run generates no more than 256 matrix jobs.
- [ ] Each batch produces a unique artifact and a per-episode report.
- [ ] One aggregation job merges reports against the latest main catalogue and is the only job allowed to write.
- [ ] A failed or missing batch prevents publication of an incomplete run.
- [ ] Unresolved episodes are reported but do not prevent other completed episodes from being inspected.
- [ ] Existing verified mappings are preserved if a new candidate conflicts or is unresolved.
- [ ] The scheduled workflow still processes a small latest-first batch and publishes only verified mappings.
- [ ] Offline tests, workflow validation, catalogue validation, and live regression checks pass.
- [ ] A full-range run demonstrates that the catalogue can be processed without one sequential 15-minute job timeout. Actual runtime and concurrency are reported rather than promised in advance.

## Dependencies
- Request 005 establishes the metadata-only enrichment pipeline and must remain compatible.
- Existing Spotify and YouTube Music schemas and publication safeguards must be reviewed before implementation.

## Open questions
- Live Spotify metadata must confirm the exact historical artist aliases and whether all older episodes follow the same compilation pattern. The implementation must be driven by observed candidate metadata, not assumptions.
- The initial batch size and maximum parallelism should be conservative and adjusted from measured per-episode timings and provider response behaviour.
- If compilation selection cannot be represented unambiguously by the current schema, document the smallest additive schema change and obtain approval before expanding scope.
