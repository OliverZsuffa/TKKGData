# Request 004: Verify YouTube Music playlists through yt-dlp

## Status
Approved as a follow-up to Requests 001 and 002 on 2026-11-09. Implementation merged to main. Live episode 150 verification is in progress.

## Context
The live audio enrichment run for episode 150 found that ytmusicapi song search did not return sufficiently corroborated candidates. A separate read-only experiment successfully extracted the official YouTube Music album playlist through yt-dlp:
- 40 playlist entries.
- 40 Spotify album tracks.
- Track titles matched after conservative punctuation normalization.
- Observed durations matched within approximately one second.

## Objective
Use yt-dlp's flat playlist metadata to verify an explicit or discovered YouTube Music playlist against the Spotify album's complete track list. Store the verified playlist and every individual song URL paired with its Spotify track URL.

## Requirements
1. Extract playlist metadata without downloading audio.
2. Verify the playlist ID, title, actual entry count, and ordered track titles.
3. Verify durations within a conservative eight-second tolerance when both providers expose duration.
4. Require every playlist entry to have a valid YouTube video ID.
5. Pair every entry with the Spotify track ID and URL from the same index.
6. Store both the playlist URL and individual song URLs.
7. Fall back to individual song search when no playlist can be verified.
8. Never publish partial, ambiguous, reordered, or mismatched tracks.
9. Keep the experiment workflow diagnostic and non-blocking.
10. Do not download audio or write mappings during a dry run.

## Acceptance criteria
- [x] Explicit playlist override uses yt-dlp flat extraction.
- [x] All entries match Spotify tracks one-to-one and in order.
- [x] Track IDs and URLs are stored for both providers.
- [x] Invalid title, count, ID, order, or duration is rejected.
- [x] Automated tests cover success and failure.
- [ ] The episode 150 dry run verifies all 40 tracks.
