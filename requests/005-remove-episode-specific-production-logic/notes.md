# Implementation notes

Approved on 2026-11-10. Implementation is in progress on branch `implement/005-episode-number-to-verified-links`.

## Implemented changes

- Replaced the spotDL command-line `save` operation with direct use of spotDL 4.5.2 metadata classes. The adapter calls the Spotify search and album metadata methods without creating a downloader or checking for FFmpeg.
- Retained spotDL in `requirements-audio.txt` because its Spotify metadata classes and configured SpotipyFree client are still used. No new repository secrets or credentials were introduced.
- Expanded YouTube Music album and playlist search variants to include the Spotify album title and the first three Spotify track titles, in addition to episode title variants.
- Added a fallback for official YouTube Music MPRE album pages that expose no OLAK playlist ID. The workflow uses yt-dlp on the album page to obtain the playable video IDs, then validates the complete ordered tracklist against Spotify.
- Preserved strict track identity, ordering, count, title, duration, video ID, TKKG artist evidence, and ambiguity checks. The individual song matching threshold remains 130.
- Added bounded candidate diagnostics to individual song fallback failures and retained the playlist discovery failure when individual song fallback also fails.
- Added stage-specific failure reporting. If Spotify metadata resolves but YouTube Music matching fails, the report still includes the Spotify album and all ordered Spotify track links.
- Added direct link output to the JSON report, terminal output, and GitHub Actions step summary. The report includes a YouTube Music playlist URL when one exists, or the verified album page URL when the album has no public playlist ID.
- Added per-stage and total timings.
- Removed the push trigger, episode-specific playlist injection, marker handling, FFmpeg installation, and experiment workflow steps.
- Made manual episode input empty by default and added a generic optional playlist ID input.
- Explicit episode selection rechecks existing verified mappings in dry-run mode. A different newly discovered mapping does not overwrite an existing verified mapping.
- Added a read-only live integration workflow with separate jobs for episodes 148, 149, and 150. The workflow runs with FFmpeg excluded from PATH, supplies only the episode number, and never publishes test results.
- Deleted `scraper/audio_source_experiments.py` and removed its current documentation references.

## Live integration results

Workflow run: https://github.com/OliverZsuffa/TKKGData/actions/runs/42821205441

All three independent dry-run jobs completed with **1 verified episode, 0 unresolved episodes**. Each episode produced 40 ordered Spotify track links and 40 ordered YouTube Music track links. Spotify track IDs and YouTube Music video IDs were unique, track numbers were contiguous from 1 through 40, and the minimum match score was 160. The matching threshold was not lowered.

| Episode | Spotify album | Verified YouTube Music album page | Spotify tracks | YouTube Music tracks | Discovery time |
|---|---|---|---:|---:|---:|
| 148 | [Spotify](https://open.spotify.com/album/0nFRzugvW1NVT1DUDxpQdb) | [YouTube Music](https://music.youtube.com/browse/MPREb_unzpFfndzd7) | 40 | 40 | 23.25 s |
| 149 | [Spotify](https://open.spotify.com/album/1OWuX6xSnnC3oebl45X28K) | [YouTube Music](https://music.youtube.com/browse/MPREb_9M8A5hcgSyo) | 40 | 40 | 24.13 s |
| 150 | [Spotify](https://open.spotify.com/album/0ZqyFeMXxCyIJvYptGlnn1) | [YouTube Music](https://music.youtube.com/browse/MPREb_ukgkcubWGzw) | 40 | 40 | 29.48 s |

The YouTube Music search results expose the correct official MPRE album pages for all three episodes, but those album records do not expose an OLAK playlist ID or video IDs through the album metadata API. yt-dlp successfully extracted the album page entries and their video IDs. The pipeline then verified all 40 ordered tracks against Spotify by normalized title, album identity, duration, and video ID.

Consequently, the report exposes the verified YouTube Music album page and all individual song URLs. The canonical `audio_release.youtube_music.playlist` remains null when no public playlist ID exists. The individual verified song mappings are still complete and usable by TKKGDownloader.

The live integration workflow ran with PATH restricted to the configured Python directory, so FFmpeg was unavailable to the discovery process. All three episodes still resolved successfully. The metadata-only Spotify lookup therefore works without installing or invoking FFmpeg.

Per-episode stage timings:
- Episode 148: Spotify 10.97 s, YouTube Music album discovery and extraction 12.28 s, total 23.25 s.
- Episode 149: Spotify 11.39 s, YouTube Music album discovery and extraction 12.74 s, total 24.13 s.
- Episode 150: Spotify 16.65 s, YouTube Music album discovery and extraction 12.83 s, total 29.48 s.

Artifacts from the integration run contain the full JSON link lists and verification evidence for each episode.

## Automated validation status

The live integration workflow passed for all three episodes on commit 750a4e405f7a38e80e56cf7d1c2bb65f23a0bdfd. The full offline unit suite and published catalogue validation also passed on that commit. A final import-only correction was applied afterward to retain CLI stderr reporting; its validation is running separately.

## Analysis of the earlier episode 149 run

Run: https://github.com/OliverZsuffa/TKKGData/actions/runs/42815546600

The old manual run completed as a GitHub Actions job but discovered zero verified mappings. It searched individual songs and rejected the first candidate set because no candidate met the unchanged corroboration threshold. Its report discarded the earlier playlist discovery failure and did not preserve candidate evidence.

The new live run resolves episode 149 successfully by discovering its official MPRE album page, extracting the ordered entries with yt-dlp, and validating all 40 tracks.

## Runtime analysis of the old run

The old run took approximately 10m26s:
- FFmpeg installation: about 7m50s.
- Python audio dependency installation: about 11s.
- Episode discovery: about 2m08s.

The new three live runs took approximately 26.61 to 31.52 seconds each, including Spotify metadata resolution and YouTube Music album extraction. This removes the previous FFmpeg installation bottleneck.
