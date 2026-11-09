# Shared audio source catalogue

## Canonical data

The episode array in data/episodes.json remains the canonical shared TKKG dataset. Audio metadata is an optional audio_release object on an episode. The generated CSV includes this object as JSON text. Existing listening_links remain official listening hubs and are not interchangeable with exact Spotify album or YouTube Music playlist URLs.

## Verified audio object

An audio object is published only after every Spotify track has one unambiguous YouTube Music song match. Titles must match exactly after conservative Unicode, case, and punctuation normalization, with additional corroboration from the TKKG artist, episode album identity, or matching duration. A full YouTube Music playlist is stored as a second entry point when it can also be verified, but playlist discovery is optional.

- spotify.album_id, spotify.url, spotify.title, spotify.track_count, and spotify.source_query
- youtube_music.tracks[] stores the Spotify track ID and URL paired with the individual YouTube Music song URL, video ID, title, artists, album, duration, and match evidence for each track
- youtube_music.playlist stores the verified album playlist ID, URL, title, and track count when available; it is null when playlist discovery fails
- youtube_music.track_count is the count of individually verified song links
- verification.status, verification.verified_at, verification.method, and verification.matched_track_count

The Spotify track count, individual YouTube Music track count, and matched track count must agree. Playlist track count must also agree when a playlist is available. Spotify track IDs, YouTube Music video IDs, and playlist IDs must agree with their corresponding URLs. The schema rejects unverified status values and unknown fields.

## Discovery

Run python -m scraper.audio_enrichment --episode 150 for a dry run. For a diagnostic or manual recovery, --playlist-id OLAK... can verify one explicitly supplied playlist with exactly one --episode; normal operation discovers the playlist automatically. Use --write only when verified results should be written to data/episodes.json and data/episodes.csv. Without an episode selector, --limit N processes at most N episodes that do not already have verified audio metadata.

Spotify metadata is resolved using spotDL's metadata save operation. YouTube Music candidates are searched using ytmusicapi. Album search results can expose an MPRE browse ID; resolve these with get_album() and use the returned audioPlaylistId when available. Playlist results may expose an OLAK ID directly or through a VLOLAK browse ID. Their public playlist track lists are then retrieved. Individual song searches are primary. A candidate needs an exact normalized title plus corroborating evidence from the TKKG artist, matching episode album, or close duration. A unique best candidate is required. Missing or ambiguous songs stop publication for that episode. Playlist discovery runs independently as an optional convenience link. A playlist is stored only if its title, TKKG artist evidence, track count, and ordered track titles all match. Multiple fully matching playlist candidates are treated as ambiguous.

The current matching rule is intentionally conservative. It does not attempt fuzzy matching, alternate-edition selection, or automatic acceptance of bonus tracks. Such episodes remain unresolved for review.

## Provider limitations

ytmusicapi is an unofficial client that emulates public YouTube Music web requests. It is not supported or endorsed by Google and can break when the service changes. The discovery workflow uses unauthenticated public access and does not store browser cookies or account credentials. No authentication, access controls, or rate limits are bypassed.

spotDL 4.5.2 supports two relevant manual pairing formats:
- YouTube Music album URL paired with the corresponding Spotify album URL. This applies to OLAK album IDs.
- Individual YouTube watch URL paired with the corresponding Spotify track URL.

A generic PL YouTube playlist is not the same type as a Spotify album. The downloader therefore uses the exact individual track pairs when a playlist cannot be paired with the Spotify album.

## Scheduled discovery

The weekly GitHub Actions run processes at most five highest-numbered episodes that do not yet have verified mappings. It writes only fully verified pairings. Manual workflow dispatch supports a specific episode or a bounded batch for historical backfill. The default manual mode is dry-run.

## Preservation

The normal episode scraper loads the previous catalogue and carries forward verified audio objects. Empty enrichment, provider failures, or changed mappings do not silently erase or replace an existing verified object. Conflicts are reported for review. The regular episode scrape remains independent of optional audio discovery.

## Downstream consumers

TKKGDownloader fetches the published episodes.json, looks up an episode by number, and uses audio_release only when verification.status is verified. It prefers the YouTube Music album URL paired with the Spotify album URL when the playlist is an OLAK album. If unavailable or unsuccessful, it pairs each youtube_music.tracks[].url with that same track's spotify_track_url. Consumers are read-only and must not maintain separate provider mappings.
