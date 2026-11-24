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
