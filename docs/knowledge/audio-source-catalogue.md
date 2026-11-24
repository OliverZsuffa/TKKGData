# Shared audio source catalogue

## Canonical episode data

The episode array in `data/episodes.json` is the canonical shared TKKG dataset. Each episode keeps its official `title`. Known spelling variants and source-title differences are stored in the optional `alternate_titles` array. Discovery uses the canonical title and these aliases without changing the official title.

Reviewed Spotify release guidance is stored on the episode in `audio_discovery.spotify`:

- `preferred_album_id`: reviewed Spotify album ID to inspect first
- `release_profile`: known album layout, such as duplicated numbering across two discs or a shared title song
- `expected_story_parts`: expected number of numbered story parts, when known

These are episode data, not a separate override configuration. The former `data/spotify_structure_overrides.json` file has been removed.

## Audio release schema version 2

An optional `audio_release` object has `schema_version: 2` and stores each provider independently.

- `spotify.album` stores Spotify album identity and metadata.
- `spotify.tracks[]` stores Spotify track number, ID, URL, original title, and available duration or artist metadata.
- `youtube_music.album` stores the YouTube Music album browse identity when available.
- `youtube_music.playlist` stores a playlist identity when available. It remains null when the album has no public playlist ID.
- `youtube_music.tracks[]` stores YouTube Music track number, video ID, URL, original title, artists, album, duration, and available matching evidence.
- `verification.spotify` and `verification.youtube_music` record provider-specific verification status and verified track counts.

Spotify and YouTube Music track counts are checked against their own lists. They are not required to be equal. Track numbering, ordering, identity, and album or playlist metadata are validated independently.

Historical records migrated from the previous paired schema retain the old pairing evidence in `youtube_music.tracks[].legacy_pairing`. This is explicitly historical provenance, not a canonical cross-provider mapping. The original verification method and timestamp are retained under `verification.migration.source_verification`. Migration does not claim a fresh provider lookup.

## Migration of existing records

The migration converted all 213 existing audio records and carried over 7,205 Spotify tracks and 7,205 YouTube Music tracks. Every original provider track ID, URL, title, available duration, artist metadata, album association, order, and matching evidence was retained. No provider was re-scraped to perform the conversion.

All 14 entries from the former override file were moved into episode records. Three known title variants were added to `alternate_titles`. The migration report is `data/audio-migration-report.json`. The previous dataset remains recoverable through the Git history at the pre-migration commit.

## Discovery status and remaining compatibility work

Spotify discovery reads `audio_discovery.spotify`, and both provider search paths use `alternate_titles`. The current automatic YouTube Music resolver still uses Spotify track matching and therefore still expects equal counts during discovery. The schema and published data can represent unequal counts, but fully independent YouTube Music album discovery remains an outstanding implementation step in Request 008.

TKKGDownloader still consumes the former paired structure. Updating that consumer is intentionally out of scope for this data migration and must be completed in a separate approved change before the new dataset is adopted by the downloader. Do not treat the new schema as downloader-compatible until that work is complete.

## Episode number to provider links

Run:

    python -m scraper.audio_enrichment --episode EPISODE_NUMBER

The episode number is the only required input. The report exposes resolved provider links and diagnostics. Use `--write` only when verified results should be written to the canonical dataset. Without an episode selector, `--limit N` processes at most N episodes that do not already have verified audio metadata. For controlled recovery, `--playlist-id PLAYLIST_ID` may be supplied only with exactly one `--episode`.

## Spotify metadata

Spotify metadata is resolved through the pinned spotDL 4.5.2 Python metadata classes directly. The workflow does not invoke the spotDL command line, instantiate its downloader, download audio, or require FFmpeg. The client uses the package's configured SpotipyFree backend and does not require repository-specific Spotify secrets.

The adapter evaluates multiple candidates across bounded query variants. It accepts the verified artist credits `TKKG` and `TKKG Retro-Archiv`. If track search is insufficient, it searches Spotify's public album catalogue and exact credited artist discographies. Candidate records are deduplicated by Spotify track ID and scored using episode number, normalized title, split-track markers, artist credit, and album context.

The resolver supports dedicated episode albums and compilation selections. Reviewed release profiles are read from the episode record. Ambiguous candidates, invalid IDs, incomplete metadata, and unexpected track structures remain unresolved.

## YouTube Music metadata

The current implementation prefers complete official album playlists, then album page extraction through yt-dlp, then individual song searches. It does not download audio. Album page URLs and playlist IDs are separate identities. A playlist ID is not invented when the provider exposes only an album browse page.

For now, the current automatic matcher still compares the YouTube Music result with Spotify track metadata. That is why episodes with different provider segmentation are represented by the schema but not yet discoverable through the normal automated flow. The next discovery implementation must verify the YouTube Music album and its track list independently, retaining every track in source order and validating its own story-part sequence.

## Preservation

The normal episode scraper carries forward existing verified audio releases. Empty enrichment, provider failures, or changed mappings must not silently erase or replace a verified provider list. Conflicts are reported for review. The migration script validates the complete candidate catalogue and restores the original files if publication fails.

## Downstream consumers

TKKGTracker and TKKGDownloader are read-only consumers of the published dataset. TKKGDownloader must be updated separately to read `spotify.tracks[]` and `youtube_music.tracks[]` independently. Until that change is complete, it is not compatible with schema version 2.
