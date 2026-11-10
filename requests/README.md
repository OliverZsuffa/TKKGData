## Request index
- [005: Episode number to verified links and metadata-only discovery](005-remove-episode-specific-production-logic/request.md) — resolve an episode number into verified Spotify album and track links plus the corresponding YouTube Music playlist and song links, remove FFmpeg and the experimental subsystem, and improve diagnostics.
- [004: Verify YouTube Music playlists through yt-dlp](004-ytdlp-playlist-verification/request.md) — verify exact ordered playlist entries and derive both provider track URLs.
- [003: Reliable data workflows](003-reliable-data-workflows/request.md) — install FFmpeg and serialize shared dataset writes.
- [002: Exact Spotify and YouTube Music track pairing](002-exact-track-pairing/request.md) — preserve exact provider track URLs for deterministic downloader matching.
- [001: Shared TKKG dataset and repository foundation](001-shared-tkkg-dataset/request.md) — establish TKKGData as the canonical dataset and define the consumer contract for TKKGTracker and TKKGDownloader.

## Request contents
- request.md: desired outcome, scope, constraints, and acceptance criteria.
- implementation-plan.md: technical approach, affected files, dependencies, and verification.
- testing.md: concrete automated and manual checks with expected results.
- notes.md: actual implementation outcomes, test results, issues, and lessons.
- attachments/: source samples and supporting material.

Request-specific plans and results stay in the request folder. Reusable verified knowledge belongs in docs/knowledge/. Explicitly approved durable decisions belong in docs/decisions.md.