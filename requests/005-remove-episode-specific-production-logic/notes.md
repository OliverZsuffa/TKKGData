# Implementation notes

Approved on 2026-11-10. Implementation is in progress on branch `implement/005-episode-number-to-verified-links`.

## Implemented changes

- Replaced the spotDL command-line `save` operation with direct use of spotDL 4.5.2 metadata classes. The adapter calls the Spotify search and album metadata methods without creating a downloader or checking for FFmpeg.
- Retained spotDL in `requirements-audio.txt` because its Spotify metadata classes and configured SpotipyFree client are still used. No new repository secrets or credentials were introduced.
- Expanded YouTube Music album and playlist search variants to include the Spotify album title and the first three Spotify track titles, in addition to episode title variants.
- Preserved strict ordered playlist validation, exact normalized title matching, track counts, duration checks, video ID checks, TKKG artist evidence, and ambiguity rejection.
- Added bounded candidate diagnostics to individual song fallback failures. The score threshold remains 130.
- Preserved the playlist discovery failure when individual song fallback also fails.
- Added stage-specific failure reporting. If Spotify metadata resolves but YouTube Music matching fails, the report still includes the Spotify album and all ordered Spotify track links.
- Added direct link output to the JSON report, terminal output, and GitHub Actions step summary.
- Added per-stage and total timing fields to discovery reports.
- Removed the push trigger, episode-specific playlist injection, marker handling, FFmpeg installation, and experiment workflow steps.
- Made manual episode input empty by default and added a generic optional playlist ID input.
- Added a read-only live integration workflow with separate jobs for episodes 148, 149, and 150. It never supplies the known playlist ID and never publishes test results.
- Deleted `scraper/audio_source_experiments.py` and removed its current documentation references.

## Validation status

Automated tests, compilation, workflow validation, catalogue validation, and the live 148/149/150 integration matrix are pending GitHub Actions results. No live episode discovery result is claimed yet.

## Analysis of the latest episode 149 run

Run: https://github.com/OliverZsuffa/TKKGData/actions/runs/42815546600

- Event: manual workflow dispatch.
- Selected episode: 149, `Tims gefährlichster Gegner`.
- Limit: 1.
- Write: enabled.
- Overall job conclusion: success.
- Discovery result: 0 verified, 1 unresolved. No catalogue mapping was committed.
- First reported failure: no sufficiently corroborated YouTube Music song match for track 1, `149 - Tims gefährlichster Gegner - Teil 01`.

The old job's green status only meant the workflow steps completed. It did not mean discovery succeeded. The old report did not include candidate evidence or the playlist failure.

## Runtime analysis of the old run

The run started at 12:24:55 UTC and completed at 12:35:21 UTC, for approximately 10m26s.

- FFmpeg installation: about 7m50s.
- Python audio dependency installation: about 11s.
- Episode discovery: about 2m08s.

This confirms that FFmpeg installation, not the matching algorithm, dominated the old run's wall-clock time. The revised workflow removes this installation. New stage timings will be recorded by the updated discovery report.

## Live integration matrix

The PR integration workflow runs episodes 148, 149, and 150 independently, with writes disabled and no explicit playlist override. Episode 150 is the positive control, episode 149 is the previous failure case, and episode 148 is independent coverage. Each job uploads a separate JSON report. An unresolved result remains diagnostic coverage, not an end-to-end pass.
