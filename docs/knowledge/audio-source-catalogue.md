# Shared audio source catalogue

## Canonical episode data

The episode array in `data/episodes.json` is the canonical shared TKKG dataset. Each episode keeps its official `title`. Known spelling variants and source-title differences are stored in the optional `alternate_titles` array. Spotify and YouTube Music discovery use the canonical title and aliases without changing the official title.

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
- `youtube_music.tracks[]` stores YouTube Music track number, video ID, URL, original title, artists, album, and available duration.
- `verification.spotify` and `verification.youtube_music` record provider-specific verification status and verified track counts.

Spotify and YouTube Music track counts are checked against their own lists. They are not required to be equal. Track numbering, ordering, identity, and album or playlist metadata are validated independently.

The original verification method and timestamp are retained under `verification.migration.source_verification`. Migration does not claim a fresh provider lookup. Historical Spotify and YouTube Music pairings are not copied into the new dataset because they are redundant with the two independent provider tracklists. The pre-migration catalogue remains recoverable through Git history.

## Migration of existing records

The migration converted all 213 existing audio records and carried over 7,205 Spotify tracks and 7,205 YouTube Music tracks. Every original provider track ID, URL, title, available duration, artist metadata, album association, order, and matching evidence was retained. No provider was re-scraped to perform the conversion.

All 14 entries from the former override file were moved into episode records. Three known title variants were added to `alternate_titles`. The migration report is `data/audio-migration-report.json`. The previous dataset remains recoverable through Git history at the pre-migration commit.

## Independent provider discovery

Spotify discovery reads `audio_discovery.spotify`. It validates the Spotify release profile and its expected story-part count against Spotify's own album tracklist.

YouTube Music discovery uses the episode number, canonical title, and `alternate_titles` to search for albums and playlists. It validates the selected YouTube Music release independently using its own album title, TKKG artist evidence, complete ordered video entries, unique video IDs, and continuous numbered story parts. Recognized extras such as Inhaltsangabe, Intro, Anfangssong, Schlußsong, and Outro are retained. It does not compare YouTube Music titles or track counts with Spotify.

A YouTube Music album browse URL and an OLAK playlist ID are stored separately. An album may be verified even when it has no public playlist ID. yt-dlp extracts playlist or album entries without downloading audio.

The current automatic resolver is conservative. Missing video IDs, incomplete tracklists, unclassified entries, duplicate IDs, title conflicts, missing TKKG artist evidence, or ambiguous album candidates remain unresolved rather than being guessed.

## Episode number to provider links

Run:

    python -m scraper.audio_enrichment --episode EPISODE_NUMBER

The episode number is the only required input. The report exposes the Spotify album URL, ordered Spotify track URLs, the YouTube Music playlist or album page URL when available, and the independently ordered YouTube Music song URLs. Use `--write` only when verified results should be written to the canonical dataset. Without an episode selector, `--limit N` processes at most N episodes that do not already have verified audio metadata. For controlled recovery, `--playlist-id PLAYLIST_ID` may be supplied only with exactly one `--episode`.

## Spotify metadata

Spotify metadata is resolved through the pinned spotDL 4.5.2 Python metadata classes directly. The workflow does not invoke the spotDL command line, instantiate its downloader, download audio, or require FFmpeg. The client uses the package's configured SpotipyFree backend and does not require repository-specific Spotify secrets.

The adapter evaluates multiple candidates across bounded query variants. It accepts the verified artist credits `TKKG` and `TKKG Retro-Archiv`. If track search is insufficient, it searches Spotify's public album catalogue and exact credited artist discographies. Candidate records are deduplicated by Spotify track ID and scored using episode number, normalized title, split-track markers, artist credit, and album context.

The resolver supports dedicated episode albums and compilation selections. Reviewed release profiles are read from the episode record. Ambiguous candidates, invalid IDs, incomplete metadata, and unexpected track structures remain unresolved.

## Provider limitations

ytmusicapi is an unofficial client that emulates public YouTube Music web requests. It is not supported or endorsed by Google and can break when the service changes. The discovery workflow uses unauthenticated public access and does not store browser cookies or account credentials. No authentication, access controls, or rate limits are bypassed.

spotDL's old paired Spotify and YouTube Music formats are not the canonical data model. TKKGDownloader still consumes the previous paired structure and must be updated separately to read the provider-specific lists before it can use schema version 2. Until that consumer change is complete, do not deploy this dataset version as the downloader's input.

## Scheduled discovery

The weekly GitHub Actions run processes at most five highest-numbered episodes that do not yet have verified audio mappings. Manual dispatch supports one episode or an inclusive start/end range. The default batch size is five and maximum parallelism is four, both bounded by validation. A preparation job partitions the selected catalogue episodes into a dynamic matrix. Each matrix job performs dry-run discovery and uploads a unique JSON report. A single aggregation job checks report completeness, merges only verified mappings, preserves existing verified mappings, validates the full catalogue, and publishes once when write mode is enabled. A failed batch or missing report blocks publication. Individual unresolved episodes remain visible in the combined report and do not by themselves block other verified mappings from being published. Manual dispatch remains dry-run by default.

## Preservation

The normal episode scraper carries forward existing verified audio releases. Empty enrichment, provider failures, or changed mappings must not silently erase or replace a verified provider list. Conflicts are reported for review. The migration script validates the complete candidate catalogue and restores original files if publication fails.
