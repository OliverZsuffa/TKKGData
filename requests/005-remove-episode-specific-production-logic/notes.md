# Implementation notes

Planning only. No production code or workflow changes have been made.

## Analysis of the latest episode 149 run

Run: https://github.com/OliverZsuffa/TKKGData/actions/runs/42815546600

- Event: manual workflow dispatch.
- Selected episode: 149, `Tims gefährlichster Gegner`.
- Limit: 1.
- Write: enabled.
- Overall job conclusion: success.
- Discovery result: 0 verified, 1 unresolved. No catalogue mapping was committed.
- First reported failure: no sufficiently corroborated YouTube Music song match for track 1, `149 - Tims gefährlichster Gegner - Teil 01`.

The job's green status only means the workflow steps completed. It does not mean discovery succeeded. The current report collapses the result to one error string and does not include the candidate evidence needed to explain the mismatch.

The current algorithm first tries to locate a matching YouTube Music album or playlist. If that fails, it falls back to individual song searches. The fallback requires an exact normalized title and a score of at least 130. An exact title alone scores 100. TKKG artist evidence adds 30 points, and matching album evidence adds 40. The reported failure therefore means no candidate in the track 1 search passed the corroboration threshold. The report does not tell us whether the candidates lacked artist/album evidence, whether their titles differed, or whether no usable candidate was returned.

The playlist failure is also discarded from the final error when the individual track fallback fails. This is a diagnostics gap. The revised implementation should preserve both the playlist failure and the rejected song candidates. The matching threshold must not be weakened without examining that evidence.

## Runtime analysis

The run started at 12:24:55 UTC and completed at 12:35:21 UTC, for approximately 10m26s.

- FFmpeg installation began at approximately 12:25:03 UTC and FFmpeg was available at approximately 12:32:53 UTC: about 7m50s.
- Python audio dependency installation ran from approximately 12:32:56 UTC to 12:33:07 UTC: about 11s.
- Episode discovery ran from approximately 12:33:07 UTC to 12:35:16 UTC: about 2m08s.

This confirms that FFmpeg installation, not the matching algorithm, dominated the run's wall-clock time. The metadata job does not process audio, so this installation should be eliminated by replacing the spotDL CLI metadata call with a tested metadata-only adapter.

## Open implementation questions

- Verify which metadata-only Spotify client or supported library interface provides the required album and track fields without FFmpeg and without adding unnecessary credentials.
- Inspect actual YouTube Music search candidates for the failed episode after diagnostics are implemented. Do not infer the exact mismatch from the current incomplete report.
- Benchmark the replacement workflow and record actual timings.

