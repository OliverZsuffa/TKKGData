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

## Episode number to provider links

Run:

    python -m scraper.audio_enrichment --episode EPISODE_NUMBER

The episode number is the only required input. The JSON report and GitHub Actions step summary expose the Spotify album URL, all ordered Spotify track URLs, the verified YouTube Music playlist or album page URL, and the ordered YouTube Music song URLs. The command also prints the resolved links. If YouTube Music discovery fails, the report retains the Spotify album and track links and identifies the failed stage.

Use --write only when verified results should be written to data/episodes.json and data/episodes.csv. Without an episode selector, --limit N processes at most N episodes that do not already have verified audio metadata. For a controlled recovery, --playlist-id PLAYLIST_ID may be supplied only with exactly one --episode.

## Spotify metadata

Spotify metadata is resolved through the pinned spotDL 4.5.2 Python metadata classes directly. The workflow does not invoke the spotDL command line, instantiate its downloader, download audio, or check for FFmpeg. The spotDL dependency remains because its Spotify client and typed metadata classes provide the existing unauthenticated metadata lookup implementation. The client uses the package's configured SpotipyFree backend and does not require repository-specific Spotify secrets.

The adapter uses spotDL's raw Spotify search results and evaluates multiple candidates across bounded query variants. Candidate records are deduplicated by Spotify track ID and scored using the exact episode number, normalized episode title, split-track marker, artist credit, and album context. Artist credits are accepted only from an explicit exact-name allowlist. The current allowlist includes TKKG and the historical credit spelling TKKG Retro-Archiv; the spelling remains subject to confirmation against live provider metadata before it is described as a confirmed catalogue-wide alias.

The resolver supports two release shapes. A dedicated episode album contributes its ordered episode tracks. A compilation contributes only the track or contiguous tracks whose titles identify the requested episode. Neighbouring episode tracks are never included. For compilation selections, album-level YouTube Music playlist pairing is deliberately disabled because the Spotify album URL points to a larger compilation. Verification therefore uses individual Spotify track and YouTube Music song pairs only. This keeps the existing audio schema safe without an additive field. Ambiguous candidates, invalid IDs, and incomplete metadata remain unresolved.

## YouTube Music playlist discovery

The preferred YouTube Music path is a complete public album playlist. Search queries are derived from the episode identity and resolved Spotify metadata, including the Spotify album title and initial track titles. ytmusicapi album and playlist searches can expose an OLAK playlist ID directly, a VLOLAK browse ID, or an MPRE album browse ID whose get_album() response may include an audioPlaylistId.

yt-dlp extracts playlist entries without downloading audio. The playlist title must identify the episode, its ID must match the requested playlist when supplied, and its complete entry count must equal Spotify's actual album track count. Every entry is paired positionally with the Spotify track list. All normalized titles must match exactly, track numbering and order must be complete, and available durations must be within eight seconds. Each resulting record stores both the Spotify track ID and URL and the YouTube video ID and URL.

Some YouTube Music album search results expose an MPRE album browse ID and a complete album tracklist but no OLAK audio playlist ID or playable video IDs in the album metadata response. In that case, the workflow opens the verified album page with yt-dlp, extracts the ordered video entries without downloading audio, and applies the same exact title, count, order, duration, and ID checks. The report exposes the verified album page URL. The canonical audio_release schema continues to store playlist as null when no playlist ID exists, while retaining every individually verified song link.

If no complete playlist can be verified, enrichment can fall back to individual YouTube Music song searches. A candidate needs an exact normalized title and a score of at least 130, based on corroborating TKKG artist, matching episode album, or close duration evidence. A unique best candidate is required. The threshold and ambiguity safeguards remain unchanged. Candidate diagnostics include bounded title, artist, album, duration, video ID, score, evidence, and rejection reason details. The final failure also retains the complete playlist discovery failure.

The matching rule is intentionally conservative. It does not attempt fuzzy matching, alternate-edition selection, or automatic acceptance of bonus tracks. Such episodes remain unresolved for review.

Current published coverage is one verified audio release mapping among 243 episodes, containing 40 ordered Spotify and YouTube Music track pairs. The Request 005 live regression matrix has additionally verified 40 ordered links each for three dry-run episodes. These test results are not published into the canonical catalogue.

## Provider limitations

ytmusicapi is an unofficial client that emulates public YouTube Music web requests. It is not supported or endorsed by Google and can break when the service changes. The discovery workflow uses unauthenticated public access and does not store browser cookies or account credentials. No authentication, access controls, or rate limits are bypassed.

spotDL 4.5.2 supports two relevant manual pairing formats:
- YouTube Music album URL paired with the corresponding Spotify album URL. This applies to OLAK album IDs.
- Individual YouTube watch URL paired with the corresponding Spotify track URL.

A generic PL YouTube playlist is not the same type as a Spotify album. The downloader therefore uses the exact individual track pairs when a playlist cannot be paired with the Spotify album.

## Scheduled discovery

The weekly GitHub Actions run processes at most five highest-numbered episodes that do not yet have verified mappings. Manual dispatch supports one episode or an inclusive start/end range. The default batch size is five and maximum parallelism is four, both bounded by validation. A preparation job partitions the selected catalogue episodes into a dynamic matrix. Each matrix job performs dry-run discovery and uploads a unique JSON report. A single aggregation job checks report completeness, merges only verified mappings, preserves existing verified mappings, validates the full catalogue, and publishes once when write mode is enabled. A failed batch or missing report blocks publication. Individual unresolved episodes remain visible in the combined report and do not by themselves block other verified mappings from being published. Manual dispatch remains dry-run by default. The separate read-only integration workflow continues to test selected episodes individually.

## Preservation

The normal episode scraper loads the previous catalogue and carries forward verified audio objects. Empty enrichment, provider failures, or changed mappings do not silently erase or replace an existing verified object. Conflicts are reported for review. The regular episode scrape remains independent of optional audio discovery.

## Downstream consumers

TKKGDownloader fetches the published episodes.json, looks up an episode by number, and uses audio_release only when verification.status is verified. It prefers the YouTube Music album URL paired with the Spotify album URL when the playlist is an OLAK album. If unavailable or unsuccessful, it pairs each youtube_music.tracks[].url with that same track's spotify_track_url. Consumers are read-only and must not maintain separate provider mappings.
