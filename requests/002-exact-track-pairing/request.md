# Request 002: Store exact Spotify track pairing URLs

## Status
Approved as a supporting change to Request 001 on 2026-11-09. Implemented and merged into main.

## Objective
For every verified YouTube Music song match, store the exact corresponding Spotify track ID and URL as well as the YouTube Music video ID and URL. This allows TKKGDownloader to use spotDL's documented manual track pairing without searching Spotify or YouTube Music again.

## Requirements
1. Each verified individual YouTube Music track mapping includes Spotify track ID and canonical Spotify track URL.
2. The Spotify ID must match the ID encoded in its URL.
3. The YouTube Music video ID must match the ID encoded in its URL.
4. Track numbers remain contiguous and ordered.
5. The Spotify and YouTube Music track mapping remains one-to-one.
6. Existing verified mappings without the new fields must not be silently rewritten as if complete. They must be re-enriched or remain incompatible with the track-level download path.
7. Playlist-level Spotify album and YouTube Music playlist mappings remain available as a separate download path.
8. No user-specific or audio file data is stored.

## Acceptance criteria
- [x] Audio schema requires Spotify track ID and URL for each individually verified match.
- [x] Enrichment extracts the Spotify ID and URL from spotDL metadata and verifies consistency.
- [x] Invalid or missing Spotify track identity rejects the mapping.
- [x] Automated tests cover valid and invalid pairings.
- [x] Dataset validation checks Spotify track ID and URL consistency.
- [x] Documentation describes the exact pairings for TKKGDownloader.
