# Implementation plan: Verify YouTube Music playlists through yt-dlp

**Status:** Approved. Implementation in progress.

1. Add a small helper around yt-dlp with extract_flat=in_playlist, skip_download, and ignoreerrors.
2. For an explicit playlist ID, build the canonical YouTube Music playlist URL and extract metadata.
3. Validate returned playlist ID and title against the episode.
4. Require playlist_count and returned entry count to equal the actual Spotify track record count.
5. Compare each entry title to the Spotify title at the same one-based track position using existing conservative normalization.
6. When both durations are available, require a difference no greater than eight seconds.
7. Extract and validate each YouTube video ID.
8. Pair the YouTube Music URL with the corresponding Spotify track URL.
9. Store the verified playlist and track mappings in audio_release.
10. For automatically discovered candidates, retain TKKG artist evidence and use yt-dlp to extract the actual playlist entries.
11. Keep ytmusicapi individual song search as a fallback when playlist verification fails.
12. Add mocked tests and run full dataset validation.
13. Pass the known episode 150 playlist ID to the push-triggered dry-run workflow.
