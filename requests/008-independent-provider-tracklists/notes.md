# Implementation notes

Status: implementation in progress. The independent provider schema, catalogue migration, episode-level discovery hints, alternate titles, and independent YouTube Music resolver are implemented on this branch.

## Preservation and migration

- Base branch: `main`
- Base commit: `3d060d3483a2a4def150c3356e8cbf9ab52ea19e`
- Migrated 213 existing audio records.
- Carried over 7,205 Spotify tracks and 7,205 YouTube Music tracks.
- Moved all 14 reviewed override entries into `audio_discovery.spotify` and `alternate_titles`.
- Added three known alternate title variants while retaining canonical episode titles.
- Removed `data/spotify_structure_overrides.json`.
- Added `data/audio-migration-report.json`.
- Regenerated `data/episodes.csv` and dataset metadata.
- No provider was re-scraped to migrate existing data. Historical pair evidence remains explicitly marked as `legacy_pairing`.

## Implementation

- `audio_release` schema version 2 stores independent provider album and track lists.
- Spotify release profiles and preferred album IDs are read from episode data.
- YouTube Music discovery searches and verifies its own album or playlist tracklist, including story-part numbering and recognized extras.
- Validation checks each provider's count against its own list. It does not compare provider counts.
- TKKGDownloader and TKKGTracker are intentionally unchanged. Downloader compatibility remains a separate follow-up before schema version 2 is consumed there.

## Checks

- The initial schema and migration test run passed 136 tests.
- The first run with independent resolver coverage reached 137 tests and exposed one outdated failure-message assertion. That assertion has been updated.
- The next full validation run is pending.
- Live audio discovery smoke tests are being checked separately from offline unit tests.
