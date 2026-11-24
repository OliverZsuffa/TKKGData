# Request 008: Independent Spotify and YouTube Music track lists

## Goal

Support official TKKG episode releases where Spotify and YouTube Music publish the same episode with different track segmentation, naming, or track counts. Episode 218 is the primary observed example: Spotify exposes 25 tracks, while the official YouTube Music album by TKKG exposes 35 tracks, including 31 story parts and four introductory or closing tracks.

The canonical dataset must be able to represent both provider releases accurately without inventing one-to-one track matches.

## Problem

The current `audio_release` contract stores YouTube Music tracks as exact pairs with Spotify tracks. Validation requires the Spotify track count, YouTube Music track count, and matched track count to be equal. YouTube Music album discovery also rejects an album when its track count differs from Spotify.

This is a valid safeguard for releases that genuinely have matching track structures, but it prevents discovery of official releases whose story parts have been split differently.

Normalising track titles alone cannot solve this because the number and boundaries of tracks differ.

## Scope

This request is limited to TKKGData.

- Replace the old paired-track `audio_release` structure with independently ordered Spotify and YouTube Music release data.
- Resolve and retain each provider's own ordered album track list, original titles, track numbers, durations, artist and album evidence, and stable provider URLs or IDs.
- Verify each provider release independently against the requested episode identity and its own internal track structure.
- Store known title variants and spelling differences in a top-level `alternate_titles` array on the episode, keeping the canonical official `title` unchanged.
- Move reviewed Spotify album IDs, release layout profiles, and expected story-part counts from `data/spotify_structure_overrides.json` into a per-episode `audio_discovery.spotify` object.
- Allow provider track counts, titles, durations, and segmentation to differ.
- Discover the official YouTube Music album as a complete album, preferring its album page and extracting playable video IDs for every entry when required.
- Remove the separate Spotify override file and read all per-episode release guidance directly from the episode dataset.
- Preserve provenance and diagnostics so unresolved or ambiguous candidates remain reviewable.
- Update schemas, catalogue validation, discovery reports, workflows, documentation, and tests within TKKGData.

## Explicit non-goals

- No changes to TKKGDownloader or TKKGTracker in this request.
- No downloader compatibility implementation or changes to download execution.
- No deletion or unnecessary re-scraping of existing Spotify or YouTube Music data.
- No loss of existing track IDs, URLs, titles, durations, album metadata, ordering, or provenance during migration.
- No fuzzy matching that silently accepts an uncertain album or track list.
- No publication of partially verified provider lists as a newly verified episode release.

## Data preservation requirements

1. The current catalogue must be snapshotted before migration so it can be restored exactly.
2. The `audio_release` schema may change to independent provider lists. The old paired structure does not need to remain the canonical format.
3. Every already scraped Spotify and YouTube Music track must be carried into the new provider-specific list. Existing YouTube Music data must not be discarded or re-scraped just because the old structure paired it with Spotify tracks.
4. Preserve original track titles, IDs, URLs, durations, album metadata, ordering, provenance, and verification status wherever those values exist.
5. Each source track must be accounted for exactly once after migration, or explicitly listed in a migration report if its fields cannot be mapped safely.
6. Do not infer missing order, metadata, or verification. Flag uncertainty for review.
7. A failed, ambiguous, incomplete, or interrupted migration or discovery must leave the original catalogue recoverable and must not partially replace the published dataset.
8. Discovery should fill genuine gaps after migration, not repeat successful scraping solely to populate the new structure.
9. New candidates must not silently overwrite existing verified provider data.
10. The complete migrated catalogue must pass schema and dataset validation before publication.
11. Reviewed Spotify discovery hints are stored on their episode records, not in a separate override file.
12. Known alternate titles are stored on the relevant episode and used consistently by Spotify and YouTube Music discovery.

## Acceptance criteria

- Episode 218 can be represented with its independently verified Spotify and YouTube Music lists even though their track counts differ.
- Provider-specific ordering and original track titles are preserved exactly as observed.
- YouTube Music story part numbering is checked independently, including the recognised intro, Inhaltsangabe, closing song, and outro entries where present.
- The validator no longer requires cross-provider track count equality for v2 records.
- The migration preserves all existing provider track data, and the new validator enforces independent provider lists.
- Existing provider tracks are migrated into the new independent structure, with no source track silently dropped.
- The override file is removed after all its values are migrated into episode records.
- Alternate title variants from the former override file are retained in the corresponding episode records.
- A failed migration or discovery cannot erase or modify existing verified data.
- Offline tests cover legacy compatibility, unequal counts, incomplete album extraction, duplicate IDs, malformed ordering, ambiguous releases, and safe preservation.
- A dry-run discovery report exposes both provider lists and all verification evidence before any write.
- The full existing test suite and published catalogue validation pass before a v2 result can be published.
