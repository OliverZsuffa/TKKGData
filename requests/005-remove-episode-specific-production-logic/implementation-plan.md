# Implementation plan

## 1. Remove the experimental subsystem and episode-specific behaviour
- Delete `scraper/audio_source_experiments.py`.
- Remove experiment execution and report upload steps from the workflow.
- Remove the push trigger and all push-event special handling, fixed playlist injection, and special commit marker. Keep scheduled and manual triggers.
- Set the manual episode input default to empty.
- Keep an optional manual playlist ID input. Permit it only when exactly one episode is explicitly selected.
- Preserve generic episode selection and bounded batch behaviour in `audio_enrichment.py`.
- Keep episode-specific test fixtures that exercise the regular enrichment pipeline.

## 2. Replace downloader-oriented Spotify metadata lookup
- Map every spotDL use and dependency in the production repository before changing dependencies.
- Evaluate a direct metadata-only interface that avoids the spotDL CLI startup check and does not require FFmpeg. Candidate approaches include a supported metadata library interface or a lightweight Spotify metadata client.
- Check authentication requirements before choosing an approach. Do not introduce client secrets or new repository secrets without a clear need and explicit documentation.
- Implement the smallest reliable approach that can resolve the first track and complete album metadata, including track IDs, album ID, track numbers, titles, artists, and durations.
- Add adapter tests using representative metadata fixtures and mocked HTTP/API responses.
- Run an integration smoke test with FFmpeg absent from PATH. It must resolve the same verified episode 150 Spotify album and track metadata currently used as regression evidence.
- Retain pinned spotDL as a metadata library dependency because the production adapter uses its `Song`, `Album`, and `SpotifyClient` classes directly. Do not invoke the spotDL CLI or initialize its downloader. Retain `ytmusicapi` and `yt-dlp` because their imports remain required.
- Do not add audio download, decode, transcode, or merge functionality to TKKGData.

## 3. Discover complete YouTube Music playlists from an episode number
- Make the episode number the only required user input for the normal lookup path.
- Resolve Spotify album metadata first, then use its album title, normalized episode title, track titles, and available artist evidence to search for YouTube Music playlist or album candidates.
- Try multiple focused query variants, prioritizing complete episode playlists rather than individual song results.
- Inspect candidate playlist metadata with yt-dlp. Compare episode and album identity, expected track count, ordered normalized titles, durations, and video IDs against the Spotify tracklist.
- Accept only a uniquely verified full playlist. Reject ambiguous or incomplete candidates. Do not weaken existing matching thresholds to force a result.
- Generate stable, directly usable Spotify album and track URLs, plus YouTube Music playlist and song URLs, from verified IDs. Clearly distinguish verified links from unverified search candidates.
- Keep individual song lookup as a secondary fallback when no complete playlist can be verified. Preserve the generic manual playlist ID override for controlled diagnostics and recovery.
- Record the exact discovery path and result for each stage so the user can see where episode-number-to-links resolution succeeded or failed.

## 4. Improve failure diagnostics for YouTube Music matching
- Preserve the playlist verification exception instead of losing it when individual song search is attempted.
- When song matching fails, include the original playlist failure in the episode failure report.
- Record bounded candidate diagnostics for each searched song: candidate title, artist names, album, duration, video ID, score, evidence, and rejection reason.
- Keep the existing score threshold and ambiguity safeguards unchanged in this request. Diagnostics must explain why candidates failed before any future decision to change matching policy.
- Add a concise GitHub Actions step summary with target count, verified count, unresolved count, and per-episode failure reason.
- Emit a GitHub Actions warning when one or more episodes remain unresolved. Keep expected discovery misses nonfatal unless the scraper itself crashes, but make the outcome unmistakable.

## 5. Current documentation
- Update README examples to use a generic episode placeholder and explain generic selection.
- Update the audio-source knowledge page to describe metadata-only dependencies and generic discovery.
- Remove references to the deleted experiment and any episode-specific production example.
- Describe current coverage numerically without identifying one episode as a special case.
- Leave historical request records intact.

## 6. Regression protection
- Keep episode-specific test fixtures in `tests/test_audio_enrichment.py`.
- Remove tests that exclusively exercise the deleted experimental script.
- Add tests for metadata lookup without FFmpeg, exact metadata field preservation, missing or malformed Spotify records, and dependency boundaries.
- Add tests that retain playlist failure details during song-search fallback.
- Add tests for song candidate diagnostics, insufficient corroboration, ambiguity, and the unchanged score threshold.
- Add workflow-level checks for no fixed episode IDs, no FFmpeg installation, no experiment step, no push-only path, and an empty manual episode default.
- Test that the workflow summary and warning accurately represent a run with zero verified mappings.

## 7. Verification and performance measurement
- Run the complete unittest suite.
- Run Python compilation for all remaining scraper modules.
- Validate the canonical catalogue and generated exports.
- Parse or lint the workflow YAML.
- Search production Python, workflow files, README, and current knowledge documentation for episode-specific identifiers and experiment references. Test fixtures and historical request records are expected exceptions.
- Run the metadata discovery smoke test with FFmpeg unavailable on PATH. The live integration workflow must also statically reject downloader CLI and FFmpeg references in the metadata adapter.
- Run live episode-number-to-links integration tests for episodes 148, 149, and 150, one episode per controlled run. Episode 150 must prove automatic playlist discovery without supplying its known playlist ID. Episode 149 must retain useful diagnostics if it remains unresolved. Episode 148 checks that discovery is not tuned only to the other two episodes.
- For each episode, record Spotify album resolution, Spotify track count and ordered links, YouTube Music playlist candidate discovery, playlist verification, ordered song links, total runtime, and final verified/unresolved status. Preserve reports as test artifacts.
- Do not publish test mappings during discovery validation. Test write/publish behaviour separately with explicit opt-in after link verification is established.
- Compare the previous run's measured stages against the new run. The previous episode 149 run spent about 7m50s installing FFmpeg, about 11s installing audio dependencies, and about 2m08s in discovery. Record actual post-change timings rather than promising a specific total runtime.
- Confirm scheduled writes and manual opt-in writes behave as intended.
