# Implementation plan

## 1. Preserve the current catalogue and plan an in-place schema migration

- The existing `audio_release` field may be changed. It is not necessary to retain the old paired-track structure as the permanent contract.
- Before changing anything, create a complete, machine-verifiable snapshot of the current catalogue and record hashes for every existing `audio_release` object.
- Inventory every episode with Spotify and/or YouTube Music data, including incomplete and partially verified records.
- The new schema will represent Spotify and YouTube Music as independent provider release objects inside `audio_release`.
- Do not create a parallel `audio_release_v2` field unless implementation reveals a concrete compatibility reason that cannot be handled by a controlled migration.
- Existing consumers may need a compatibility period, but the canonical data should not retain the flawed one-to-one pairing as its source of truth.

## 2. Define the new independent provider structure

- Replace the old paired-track layout with a versioned `audio_release` object containing independent `spotify` and `youtube_music` album metadata and ordered track lists.
- Keep strict `additionalProperties: false` validation.
- Proposed shape:

```json
{
  "audio_release": {
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

## 6. Migrate existing scraped data without losing it

- Build a deterministic migration that reads every existing `audio_release` record and maps its Spotify and YouTube Music fields into the corresponding independent provider lists.
- Carry over every already scraped YouTube Music track, including its original title, video ID, URL, duration, artist metadata, album association, track order, and any other available source fields. Do not discard a track merely because its former Spotify pair is no longer meaningful.
- Carry over all existing Spotify tracks in the same way. Do not re-scrape either provider just to perform the structural migration.
- Preserve provider order exactly as represented by the existing data. Where the old pairing obscures original album order or numbering, retain the available sequence and flag uncertainty for review rather than guessing.
- Preserve existing album IDs, URLs, playlist IDs, source metadata, verification timestamps, and provenance wherever present.
- Do not claim that migrated data has been freshly verified. Retain its existing verification status and record that it was structurally migrated from the previous schema.
- If existing records contain only one provider, migrate that provider independently. Missing provider data stays missing and can be discovered later.
- Generate a migration report listing migrated episodes, track counts before and after for each provider, fields that could not be mapped, and any records requiring manual review.
- Compare pre-migration and post-migration inventories. Every source track must be accounted for exactly once in the corresponding provider list, or explicitly listed in the migration report as unresolved. No silent drops.
- Keep a recoverable pre-migration snapshot. Write the migrated catalogue to a temporary file, validate the complete candidate catalogue, run preservation assertions, and only then replace the canonical dataset.
- If any migration check fails, abort the write and leave the original catalogue untouched.
- New discovery results may enrich missing metadata, but must not overwrite existing verified provider data without an explicit conflict resolution.
- Preserve the existing issue-ledger behaviour and do not let a successful Spotify-only lookup clear an issue when the YouTube Music side remains unresolved.

## 7. Update validation and documentation

- Add strict JSON Schema definitions for independent provider album metadata, provider track records, and verification counts.
- Update `scraper/validate.py` to validate the migrated `audio_release` structure.
- Compare each provider's declared count to its own list length and verified count. Do not compare Spotify count to YouTube Music count.
- Keep a temporary legacy input reader or migration utility only as long as needed to migrate existing records and support rollback.
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

The fixtures should include complete real provider metadata and source provenance captured from discovery. In addition, use the actual current catalogue as a migration fixture. Include records with both providers, only one provider, legacy track pairs, extras, and incomplete metadata. If a full observed list is unavailable, keep that episode as a live dry-run case rather than inventing fixture entries.

## 9. Tests and release gates

- Schema tests for the new independent provider structure and for legacy records accepted by the migration reader.
- Migration tests proving every existing Spotify and YouTube Music track is carried over exactly once with its original metadata and order wherever known.
- Regression tests proving the pre-migration catalogue snapshot can be restored exactly.
- Unequal provider track count tests.
- Provider-specific track ordering and numbering tests.
- YouTube Music extras and variable part count tests.
- Duplicate IDs, missing IDs, null entries, incomplete extraction, gaps, duplicate part numbers, and unrelated episode track tests.
- Ambiguous album candidate and wrong artist tests.
- Preservation tests proving failed or interrupted migration cannot modify the original catalogue.
- Tests proving a failed provider discovery cannot erase migrated data or existing verified provider lists.
- Conflict tests proving a new result cannot silently replace an existing verified mapping.
- Atomic write tests proving invalid candidate data never replaces the published catalogue.
- Run the full offline test suite, schema validation, dataset validation, Python compilation, and workflow syntax checks.
- Run dry-run discovery for the representative episodes. Inspect the complete provider lists before any write.
- Only after the migration report and provider dry-run results are reviewed should the migrated catalogue be published. New discovery should only fill genuine gaps or resolve flagged uncertainty.

## 10. Out of scope follow-up

TKKGDownloader must later be updated to prefer the v2 independent provider lists and download the YouTube Music list in its own order. That work belongs in a separate approved request in the TKKGDownloader repository. Until then, v2 is data-only and existing downloader behaviour continues to use the legacy field.
