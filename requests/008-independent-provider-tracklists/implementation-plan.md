# Implementation plan

## 1. Freeze and document the existing contract

- Treat the current `audio_release` field as the legacy v1 contract.
- Do not weaken or reinterpret its schema, validation, or downstream meaning.
- Add regression tests that load representative existing verified records and assert that their parsed values and serialized JSON remain unchanged.
- Capture a baseline of the current catalogue before implementation. Record the current `audio_release` objects, their episode numbers, and a content hash so tests can detect accidental modifications.
- Keep existing preservation logic in place. A new discovery result must not replace a legacy verified mapping.

## 2. Add a separate v2 field

- Introduce an optional sibling field, provisionally named `audio_release_v2`, in the episode schema.
- Do not place v2 records inside the legacy `audio_release` object.
- Version the new object explicitly and keep strict `additionalProperties: false` validation.
- Proposed shape:

```json
{
  "audio_release_v2": {
    "schema_version": 2,
    "spotify": {
      "album": {
        "album_id": "...",
        "url": "https://open.spotify.com/album/...",
        "title": "...",
        "artist_names": ["TKKG"],
        "track_count": 25,
        "source_query": "..."
      },
      "tracks": [
        {
          "track_number": 1,
          "track_id": "...",
          "url": "https://open.spotify.com/track/...",
          "title": "...",
          "duration_seconds": 180.0,
          "artist_names": ["TKKG"]
        }
      ],
      "track_count": 25
    },
    "youtube_music": {
      "album": {
        "browse_id": "...",
        "url": "https://music.youtube.com/browse/...",
        "playlist_id": null,
        "playlist_url": null,
        "title": "...",
        "artist_names": ["TKKG"],
        "track_count": 35
      },
      "tracks": [
        {
          "track_number": 1,
          "video_id": "...",
          "url": "https://music.youtube.com/watch?v=...",
          "title": "...",
          "duration_seconds": 70.0,
          "artist_names": ["TKKG"]
        }
      ],
      "track_count": 35
    },
    "verification": {
      "status": "verified",
      "verified_at": "...",
      "method": "independent_provider_album_verification",
      "spotify_verified_track_count": 25,
      "youtube_music_verified_track_count": 35
    }
  }
}
```

This is a design proposal, not a final frozen schema. Confirm actual provider metadata availability before deciding which fields are required or nullable. Preserve the original provider title and album title. Do not fabricate missing duration, artist, browse ID, or playlist ID values.

- Store a YouTube Music album page URL even when there is no public OLAK playlist ID. Keep playlist identity separate from album browse identity.
- If Spotify track-level IDs or URLs cannot be retrieved reliably, do not invent them. Record only fields supported by the actual source and define the verification threshold accordingly.
- Avoid duplicating fields that can be derived safely, but retain explicit track counts if they make validation and consumer access clearer.

## 3. Implement provider-specific discovery

### Spotify

- Keep the current Spotify resolver and its release classification safeguards.
- Resolve the selected episode release and retrieve its complete ordered track list.
- Preserve Spotify's own track numbering, titles, IDs, URLs, artist credits, album identity, and durations.
- Verify that the album or compilation selection belongs to the requested episode and does not accidentally include neighbouring episodes.
- Do not require the Spotify track list to resemble the YouTube Music list.

### YouTube Music

- Search for the official episode album using episode number, canonical title, known title variants, and artist identity.
- Treat the TKKG artist identity and episode identity as independent evidence. A matching title alone is insufficient.
- Retrieve the album's complete track list from ytmusicapi where available.
- When album metadata does not expose playable video IDs, extract the official album page through yt-dlp without downloading audio.
- Preserve every entry in source order, including Inhaltsangabe, intro or Anfangssong, all numbered story parts, Schlußsong, and outro when present.
- Parse and validate numbered story parts independently. Recognise known naming variants such as `Teil 01`, `Teil 1`, and episode-prefixed titles, while retaining the original title unchanged.
- Detect duplicate video IDs, missing entries, null extraction entries, duplicate part numbers, gaps in part numbering, unexpected episode identities, and ambiguous album candidates.
- Do not assume a fixed number of story parts or extras.
- Do not reject a complete YouTube Music album solely because its count differs from Spotify.

## 4. Define independent verification rules

### Spotify verification

- Valid album and track identifiers and URLs.
- Exact episode identity supported by album metadata and track titles.
- Complete ordered album track extraction.
- Unique track IDs.
- Valid and internally consistent track numbering.
- Recognised compilation boundaries where applicable.

### YouTube Music verification

- Valid album browse identity or a verified album page URL.
- Strong TKKG artist evidence and episode identity.
- Complete album track extraction, with no null or missing entries.
- Valid unique video IDs and matching watch URLs for every track.
- Original album order retained and track numbers contiguous.
- Story part numbers form a complete sequence when the release uses numbered parts.
- Recognised extras are retained and classified without being mistaken for story parts.
- No unrelated neighbouring episode tracks are silently included.

### Cross-provider checks

- Confirm that both independently verified releases identify the same episode using episode number, title, artist, and available album metadata.
- Use total duration, where available, as supporting evidence only. Different segment boundaries make per-track duration comparison invalid.
- Never require equal track counts, equal track titles, equal track numbering, or one-to-one track correspondence.
- Keep uncertainty explicit. If the identity of either provider release is ambiguous, do not mark the combined v2 object verified.

## 5. Add a dry-run report before writing

- Extend the episode discovery report to show Spotify and YouTube Music album metadata and track lists separately.
- Show provider-specific track counts, total duration where available, original order, part classification, IDs, URLs, and verification evidence.
- Show rejected candidates and precise failure stages.
- Make it obvious that different track counts are expected and are not themselves a failure.
- Keep dry-run as the default.
- Do not update the canonical dataset unless the user explicitly enables write mode.

## 6. Preserve existing data during writes

- Load the current catalogue and retain all legacy fields.
- Write a new `audio_release_v2` object only after both provider lists pass all checks.
- If an episode already has a verified v2 object, compare the new result with it. Do not silently replace a different verified mapping. Report a conflict for review.
- If an episode has a verified legacy `audio_release` object, preserve it exactly. The v2 object may coexist with it, but discovery must not convert or delete the legacy object.
- Write the catalogue through a temporary file, validate the complete candidate catalogue, then replace the target file only after validation succeeds.
- Ensure CSV generation and dataset metadata updates happen only after the validated JSON candidate is ready.
- Preserve the existing issue-ledger behaviour and do not let a successful Spotify-only lookup clear an issue when the YouTube Music side remains unresolved.

## 7. Update validation and documentation

- Add strict JSON Schema definitions for v2 provider album metadata, provider track records, and independent verification counts.
- Update `scraper/validate.py` so legacy and v2 objects are validated separately.
- For v2, compare each provider's declared count to its own list length and verified count. Do not compare Spotify count to YouTube Music count.
- Keep all existing v1 checks unchanged.
- Update the audio source catalogue documentation to explain both contracts and the compatibility period.
- Update the README's published coverage statement only after actual data publication changes the coverage.
- Add a documented future migration policy. Do not bulk migrate existing records as part of this request.

## 8. Regression fixtures and rollout matrix

Use observed source records, not invented IDs or guessed album metadata.

- Episode 218: primary fixture, Spotify 25 tracks versus YouTube Music 35 tracks, with 31 story parts and the observed extras.
- Episode 225: larger segmentation difference, Spotify 24 versus YouTube Music 45.
- Episode 228: compilation-shaped Spotify release and a distinct YouTube Music album representation.
- Episode 236: larger list difference, Spotify 33 versus YouTube Music 62.
- Episode 240: Spotify 38 versus YouTube Music 73.
- Episode 150: existing 40-track legacy mapping, used to prove v1 compatibility.
- Episode 226: retain as a separate Spotify resolution failure. Do not misclassify it as a YouTube Music segmentation issue.

The fixtures should include complete real provider metadata and source provenance captured from discovery. If a full observed list is unavailable, keep that episode as a live dry-run case rather than inventing fixture entries.

## 9. Tests and release gates

- Schema tests for valid v1 and v2 objects.
- Regression tests proving all existing v1 fixtures still pass unchanged.
- Unequal provider track count tests.
- Provider-specific track ordering and numbering tests.
- YouTube Music extras and variable part count tests.
- Duplicate IDs, missing IDs, null entries, incomplete extraction, gaps, duplicate part numbers, and unrelated episode track tests.
- Ambiguous album candidate and wrong artist tests.
- Preservation tests proving failed or interrupted v2 discovery cannot modify v1 or existing v2 data.
- Conflict tests proving a new result cannot silently replace an existing verified mapping.
- Atomic write tests proving invalid candidate data never replaces the published catalogue.
- Run the full offline test suite, schema validation, dataset validation, Python compilation, and workflow syntax checks.
- Run dry-run discovery for the representative episodes. Inspect the complete provider lists before any write.
- Only after the dry-run results are approved should v2 write mode be enabled for selected episodes.

## 10. Out of scope follow-up

TKKGDownloader must later be updated to prefer the v2 independent provider lists and download the YouTube Music list in its own order. That work belongs in a separate approved request in the TKKGDownloader repository. Until then, v2 is data-only and existing downloader behaviour continues to use the legacy field.
