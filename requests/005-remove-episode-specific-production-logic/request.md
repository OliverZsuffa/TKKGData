# Request 005: Remove episode-specific logic and streamline metadata discovery

## Status
Planning only. Awaiting approval of this revised scope.

## Context
Episode numbers are ordinary catalogue data. Production code, workflows, and current operational documentation must not contain special handling for an individual episode. Episode-specific regression fixtures may remain in tests.

The current audio enrichment workflow installs the full FFmpeg system package before it searches for metadata. FFmpeg is an audio processing tool and does not belong in a metadata discovery job. The current Spotify metadata lookup invokes the spotDL command line interface, which performs an FFmpeg availability check even when using its metadata-only `save` command. The workflow therefore installs FFmpeg solely to satisfy a downloader-oriented command path.

The latest manual run for episode 149 completed as a GitHub Actions job but discovered no verified mappings. It spent approximately 7 minutes 50 seconds installing FFmpeg, then approximately 11 seconds installing Python audio dependencies, and approximately 2 minutes 8 seconds in discovery. The discovery report says the first YouTube Music track had no sufficiently corroborated song match. The report does not preserve the rejected candidates or the earlier playlist verification failure, so the actual reason cannot be diagnosed from the report alone.

## Desired outcome
A generic, fast, metadata-only enrichment pipeline that takes an episode number and resolves it into verified Spotify album and track links plus the corresponding YouTube Music playlist and track links. It must not install or require FFmpeg, must remove the separate experimental subsystem, report useful evidence when matching fails, and publish only fully verified mappings.

## Scope
- Remove `scraper/audio_source_experiments.py`, its dedicated workflow steps, report upload, tests specific to that script, and current documentation references.
- Remove all fixed episode and playlist assumptions from production code, workflow configuration, and current operational documentation. Keep episode-specific regression fixtures in tests.
- Remove the push-triggered experiment and publication path. Keep scheduled enrichment and manual dispatch.
- Make manual episode selection empty by default. Keep an optional explicit playlist ID override for one explicitly selected episode.
- Replace the spotDL command line metadata lookup with a metadata-only Spotify lookup that does not require FFmpeg or audio processing. Investigate the smallest maintained approach that works without introducing unnecessary credentials or secrets. Prefer a supported metadata API or library interface over invoking a downloader CLI. Do not settle on a replacement until it has been tested in an environment where FFmpeg is unavailable.
- Remove spotDL and other dependencies that become unnecessary after checking all production imports. Keep only dependencies needed for Spotify metadata, YouTube Music search, playlist inspection, and catalogue validation.
- Remove the FFmpeg installation step and `apt-get update` from the metadata workflow.
- Make episode-number-to-links the central user-facing workflow: given an episode number, resolve the canonical episode identity, Spotify album URL and track URLs/IDs, then discover the corresponding YouTube Music playlist URL and ordered song/video links. Return a clear per-stage result and never label an unverified candidate as a verified link.
- Generalize the known-good episode 150 process. Discover YouTube Music playlist candidates from Spotify album metadata, including album title, normalized episode title, track titles, and available artist evidence. Inspect candidate playlists with yt-dlp and score them using episode/album identity, track count, ordered normalized title matches, durations, and stable video IDs. Accept only a candidate that passes the existing strict full-playlist verification. Reject ambiguous candidates rather than guessing. Individual song search remains a secondary fallback.
- Keep a generic explicit playlist ID override for one selected episode as a diagnostic and recovery mechanism, not as an episode-specific production rule.
- Preserve the existing Spotify album and track validation, YouTube Music playlist and song verification, ordering, identity checks, and publication safeguards.
- Improve discovery diagnostics. Preserve the playlist discovery failure when falling back to individual song searches. For rejected song candidates, record safe diagnostic evidence such as title, artist, album, duration, score, and rejection reason. Avoid recording irrelevant or excessive response data.
- Make workflow summaries distinguish a successfully executed job from a discovery result with unresolved episodes. Show verified and unresolved counts and emit a visible warning when nothing was verified.
- Update the README and current audio-source knowledge documentation to describe generic metadata-only discovery and the new dependency boundary.
- Record and compare stage timings so the effect of removing FFmpeg can be measured.

## Out of scope
- Downloading or processing audio in TKKGData.
- Changing TKKGTracker or TKKGDownloader.
- Weakening verification thresholds merely to force a match.
- Publishing partially verified mappings.
- Changing the canonical catalogue schema unless a separately justified requirement emerges.

## Acceptance criteria
1. No production Python source or workflow file contains a hardcoded episode number, title, or playlist ID for a particular episode.
2. The experimental diagnostic subsystem and its workflow/report integration are removed.
3. The Spotify metadata lookup succeeds in a clean test environment where FFmpeg is not installed or available on PATH.
4. The metadata workflow contains no FFmpeg installation or audio processing step.
5. No downloader-only dependency remains unless a production discovery import demonstrably requires it.
6. Existing exact Spotify track identity and YouTube Music verification checks remain intact.
7. Failed playlist discovery details and individual song candidate rejection evidence are retained in the report.
8. Workflow summaries clearly show verified and unresolved results, without presenting an unresolved discovery as a successful enrichment.
9. Manual dispatch has no episode-specific default and supports a generic selected episode with an optional explicit playlist override.
10. Scheduled enrichment continues to process a bounded set of missing mappings and publish only verified results.
11. Offline tests, Python compilation, workflow syntax checks, dependency checks, and catalogue validation pass.
12. A controlled before/after timing comparison confirms that FFmpeg installation is eliminated and records the new discovery runtime.
13. From an episode number alone, the pipeline can produce a verified Spotify album link, all ordered Spotify track links, a verified YouTube Music playlist link, and all ordered YouTube Music track links, or a precise stage-specific failure report.
14. Live integration tests cover episodes 148, 149, and 150. Episode 150 is the known positive control and must be rediscovered without a hardcoded playlist ID. Episode 149 is the known previous failure and must produce actionable diagnostics even if it remains unresolved. Episode 148 is an independent episode coverage test. Report results separately and do not count an unresolved episode as a successful test.

## Known investigation target
Run 42815546600:
https://github.com/OliverZsuffa/TKKGData/actions/runs/42815546600

Episode 149, `Tims gefährlichster Gegner`, was selected with limit 1 and write enabled. The job conclusion was success, but the report contained zero verified mappings and one unresolved episode. The first failing individual song lookup was track 1, `149 - Tims gefährlichster Gegner - Teil 01`.
