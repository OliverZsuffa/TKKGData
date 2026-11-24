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

- Introduce an additive, independently versioned audio metadata structure for Spotify and YouTube Music.
- Resolve and retain each provider's own ordered album track list, original titles, track numbers, durations, artist and album evidence, and stable provider URLs or IDs.
- Verify each provider release independently against the requested episode identity and its own internal track structure.
- Allow provider track counts, titles, durations, and segmentation to differ.
- Discover the official YouTube Music album as a complete album, preferring its album page and extracting playable video IDs for every entry when required.
- Keep the existing `audio_release` object and its validation contract unchanged for compatibility.
- Preserve provenance and diagnostics so unresolved or ambiguous candidates remain reviewable.
- Update schemas, catalogue validation, discovery reports, workflows, documentation, and tests within TKKGData.

## Explicit non-goals

- No changes to TKKGDownloader or TKKGTracker in this request.
- No downloader compatibility implementation or changes to download execution.
- No automatic migration or rewriting of existing legacy `audio_release` objects.
- No deletion, renumbering, replacement, or re-pairing of existing Spotify or YouTube Music tracks.
- No fuzzy matching that silently accepts an uncertain album or track list.
- No publication of partially verified provider lists as a verified episode release.

## Data preservation requirements

1. Existing `audio_release` values must remain byte-for-byte unchanged for episodes not explicitly changed by a separate approved operation.
2. The new representation must live in a separate optional field, provisionally `audio_release_v2`, rather than changing the meaning of the existing field.
3. Existing consumers and validators must continue to accept the legacy structure.
4. Discovery must never replace a verified legacy mapping merely because a new discovery run found a different candidate.
5. A new v2 mapping is written only after both provider lists independently pass their verification requirements.
6. A failed, ambiguous, incomplete, or interrupted discovery must leave both the old data and any previously verified v2 data untouched.
7. Catalogue writes must be atomic at the dataset level: validation happens before publication, and a failed run must not leave a partially updated catalogue.
8. The migration is additive. No bulk conversion of historical records is included.

## Acceptance criteria

- Episode 218 can be represented with its independently verified Spotify and YouTube Music lists even though their track counts differ.
- Provider-specific ordering and original track titles are preserved exactly as observed.
- YouTube Music story part numbering is checked independently, including the recognised intro, Inhaltsangabe, closing song, and outro entries where present.
- The validator no longer requires cross-provider track count equality for v2 records.
- The validator still enforces the complete existing legacy contract for `audio_release`.
- Existing legacy records remain unchanged and continue to pass validation.
- A failed v2 discovery cannot erase or modify existing verified data.
- Offline tests cover legacy compatibility, unequal counts, incomplete album extraction, duplicate IDs, malformed ordering, ambiguous releases, and safe preservation.
- A dry-run discovery report exposes both provider lists and all verification evidence before any write.
- The full existing test suite and published catalogue validation pass before a v2 result can be published.
