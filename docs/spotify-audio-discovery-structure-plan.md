# Spotify audio discovery: catalogue structure changes

## Status

Planning document. This is a proposed implementation, not implemented behaviour.

## Source and audit context

This plan is based on the manual review of episodes returned by the latest Audio coverage audit reviewed on 23 November 2026.

- Audit workflow: [Audio coverage audit runs](https://github.com/OliverZsuffa/TKKGData/actions/workflows/audio-coverage-audit.yml). This opens the workflow run history. The exact run ID was not available in the review context, so it is intentionally not guessed.
- Audit workflow is read-only and separates Ready for discovery from Needs investigation.
- Episodes 19, 20, 37 and 128 were reported as not found on Spotify during this manual review and are being left unresolved for now.
- This review identified title variations and structural changes in Spotify album listings, especially from episode 218 onward.

## Goals

1. Add verified alternate episode titles and exact Spotify album overrides for known cases.
2. Support albums containing two discs or extended track counts.
3. Detect and exclude extras such as summaries, opening songs, closing songs and outros.
4. Handle the new album layout from episode 218 onward without hardcoding each future episode's part count.
5. Preserve conservative verification, diagnostics and protection of existing verified catalogue entries.

## Confirmed title exceptions

Canonical catalogue titles must remain unchanged. Alternate Spotify titles should be used as additional resolver inputs.

| Episode | Spotify title | Notes |
| --- | --- | --- |
| 48 | Bestien der Finsternis | Catalogue title reportedly differs by the word `der` versus `in der`. |
| 94 | In dunkler Nacht am Marmor-Grab | Confirmed alternate title. Verify canonical title from catalogue before implementation. |
| 110 | Das Phantom im Schokoladenmuseum | Confirmed alternate title. Verify canonical title from catalogue before implementation. |

Alternate-title matching should be applied consistently to track search, album search and artist-discography candidate filtering, while retaining the canonical title as the user-facing title.

## Confirmed Spotify album overrides

| Episode | Spotify album ID | Link |
| --- | --- | --- |
| 48 | 4WgadnXmyPlFzQ6GyHUqRw | https://open.spotify.com/album/4WgadnXmyPlFzQ6GyHUqRw |
| 94 | 0in2tMW0QlYkCN4xZGMKFw | https://open.spotify.com/album/0in2tMW0QlYkCN4xZGMKFw |
| 175 | 7z37XBrYgYo7DCs9dFeHvq | https://open.spotify.com/album/7z37XBrYgYo7DCs9dFeHvq |
| 200 | 40AzKKVoE6d4TxqlZ2N4Fr | https://open.spotify.com/album/40AzKKVoE6d4TxqlZ2N4Fr |
| 218 | 1JBdOPbN661RjpdWNm9Xfo | https://open.spotify.com/album/1JBdOPbN661RjpdWNm9Xfo |
| 219 | 65b6rQAtUIFQAySC4lDKpL | https://open.spotify.com/album/65b6rQAtUIFQAySC4lDKpL |

Episode 110 is confirmed by title but no album URL was supplied. Episodes 220 onward should initially be resolved automatically unless later confirmed IDs are added.

## Known episode structures

### Episode 175: two-disc, duplicated part numbering

One album represents two discs, each containing parts 01 through 40. Disc identity or explicit part suffixes (A and B) must be used to distinguish the segments. Do not treat repeated part numbering as duplicates across a single 40-part episode. The combined episode should contain 80 ordered parts, with a stable ordering of disc A followed by disc B.

### Episode 200: extended 80-part album

The album has parts 01 through 80. The resolver and validation must not assume a 40-part episode ceiling.

### Episodes 218 and 219: structured extras

Album sequence:

1. Inhaltsangabe
2. Anfangssong
3. Numbered episode parts
4. Schlußsong
5. Outro

Episode 218 has 21 numbered parts. Episode 219 has 19 numbered parts.

### Episode 220 onward: shared title song and extras

Album sequence:

1. Inhaltsangabe
2. TKKG Titelsong
3. Numbered episode parts
4. TKKG Schlußsong
5. Outro

Observed part counts:

| Episode | Parts |
| --- | ---: |
| 220 | 19 |
| 221 | 21 |
| 222 | 21 |
| 223 | 21 |
| 224 | 23 |
| 225 | 20 |
| 226 | 21 |
| 227–243 | Not yet individually confirmed |

Part counts must be inferred from album track metadata and sequence, rather than assumed or hardcoded for episodes 227–243.

## Proposed implementation

### 1. Central override configuration

Introduce a dedicated configuration file for resolver exceptions. Suggested fields:

- Episode number
- Alternate titles
- Exact Spotify album ID, if confirmed
- Album structure profile
- Optional disc ordering or part mapping rules
- Optional expected part count, when independently confirmed

Keep this separate from the main episode catalogue unless the project decides that provider-specific override data belongs in the published catalogue schema.

### 2. Resolver changes

- Prefer exact album IDs for configured episodes.
- Add alternate titles to candidate search generation and candidate validation.
- Preserve existing artist and metadata evidence checks.
- Do not weaken generic matching thresholds to compensate for these special cases.
- Record which override or profile was used in the report for traceability.

### 3. Album track classifier

Classify album tracks as:

- Episode part, with extracted part number
- Inhaltsangabe
- Anfangssong or Titelsong
- Schlußsong
- Outro
- Unknown

Only validated episode parts should be mapped as episode audio. Extras should be excluded from the episode track mapping. Unknown tracks should trigger diagnostics and should not be silently included.

### 4. Structure profiles

Implement reusable profiles rather than per-episode procedural special cases:

- Standard numbered episode
- Two-disc episode with repeated numbering and disc ordering
- Extended numbered episode
- Structured album with summary, opening song, episode parts, closing song and outro
- Structured album with a shared title song

Profiles should be selected from explicit overrides when known, otherwise detected conservatively from metadata and track sequence.

### 5. Validation and safety

Before accepting a resolved mapping:

- Part numbering is numeric and ordered.
- Numbering begins at 1 and is continuous.
- No duplicate part numbers exist within the resolved episode sequence.
- Disc-specific repeated numbers are interpreted only under a configured or verified multi-disc structure.
- Extras are excluded from mapped episode parts.
- Unknown tracks are reported.
- Detected part count is reported and compared with any configured expected count.
- Existing verified mappings are not replaced automatically by differing results.
- Failure to classify or validate the album leaves the episode unresolved and provides diagnostics.

### 6. Diagnostics and audit integration

Reports should expose the detected profile, selected album ID, track classification, disc ordering, part count, excluded extras, unknown tracks and validation failures.

The coverage audit should continue to distinguish episodes ready for discovery from episodes with recorded issues. Resolver-specific diagnostics should help explain whether a failure is a search failure, title mismatch, unsupported album structure or track-validation failure.

### 7. Regression tests

Add fixtures and tests for:

- Alternate-title matching for 48, 94 and 110
- Exact album overrides for the confirmed album IDs
- Two-disc episode 175 with duplicated part numbers across discs
- Episode 200 with 80 parts
- Episodes 218 and 219 with structured extras and different part counts
- Episode 220 profile with a shared title song
- Variable part counts in the 220 onward profile
- Unknown track handling
- Missing, duplicate and discontinuous part numbers
- Standard episode behaviour and matching thresholds remaining unchanged
- Existing verified mapping preservation

Use synthetic or sanitized metadata fixtures where possible. Tests must not depend on live Spotify access.

## Implementation phases

1. Add and validate the override configuration format.
2. Implement alternate title and exact album override support.
3. Implement reusable album structure profiles and track classification.
4. Implement profile-aware validation and diagnostics.
5. Add regression tests for confirmed structures and generic behaviour.
6. Review the resulting report format and audit integration.
7. Open a pull request with CI results for review before merging.

## Explicitly out of scope

- Manually resolving episodes 19, 20, 37 and 128 at this stage.
- Guessing Spotify mappings where evidence is insufficient.
- Hardcoding the part counts for episodes 227 through 243.
- Weakening verification thresholds globally.
- Automatically replacing existing verified mappings.

## Review notes

The episode structure observations and confirmed links in this plan are based on the manual audit follow-up on 23 November 2026. Episodes 227 through 243 were identified as having variable part counts, but their individual counts and album metadata have not yet been verified.
