# Development requests

Every substantial change is tracked in its own numbered request folder.

## Workflow
1. Read project instructions and relevant knowledge.
2. Investigate the existing implementation and sources only as far as needed.
3. Create request.md, implementation-plan.md, testing.md, and notes.md.
4. Present the plan and wait for Oliver's explicit approval.
5. Implement only the approved scope on a focused branch.
6. Run automated checks, source validation, and relevant manual tests.
7. Record actual results and remaining work in notes.md.
8. Request explicit approval before merging or deploying.

## Request index
- [004: Verify YouTube Music playlists through yt-dlp](004-ytdlp-playlist-verification/request.md) — verify exact ordered playlist entries and derive both provider track URLs.
- [003: Reliable data workflows](003-reliable-data-workflows/request.md) — install FFmpeg and serialize shared dataset writes.
- [002: Exact Spotify and YouTube Music track pairing](002-exact-track-pairing/request.md) — preserve exact provider track URLs for deterministic downloader matching.
- [001: Shared TKKG dataset and repository foundation](001-shared-tkkg-dataset/request.md) — establish TKKGData as the canonical dataset and define the consumer contract for TKKGTracker and TKKGDownloader.

## Request contents
- request.md: desired outcome, context, scope, constraints, and acceptance criteria.
- implementation-plan.md: technical approach, affected files, dependencies, and verification.
- testing.md: concrete automated and manual checks with expected results.
- notes.md: actual implementation outcomes, test results, issues, and lessons.
- attachments/: source samples and supporting material.

Request-specific plans and results stay in the request folder. Reusable verified knowledge belongs in docs/knowledge/. Explicitly approved durable decisions belong in docs/decisions.md.
