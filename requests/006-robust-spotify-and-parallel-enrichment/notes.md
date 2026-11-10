# Implementation notes

## Status
The approved implementation is on the Request 006 branch. No canonical catalogue data has been changed or published. Pull request #15 is open and awaiting completion of the latest parallel smoke workflow and representative live discovery run.

## Investigation findings
- The original resolver used one Spotify search result and required the artist credit to be exactly \`TKKG\`.
- Historical tracks use both \`TKKG\` and \`TKKG Retro-Archiv\` artist credits. The verified aliases are explicit and unrelated artists are rejected.
- The free spotDL Spotify client does not expose album-name search. Historical compilation discovery uses SpotAPI's public album search and paginated artist discographies, followed by full album metadata validation.
- A public Spotify page is indexed for \`07/3er Box - Folge 19-21\`: https://open.spotify.com/intl-de/album/0f3YoQoLsSQbXI8Cp34lR2. However, the current Spotify metadata search and exact artist discographies do not return that album or its tracks in the German-market API results. It is therefore not safe to publish it as a verified episode 20 mapping. The resolver leaves episode 20 unresolved rather than hardcoding an unverified album ID.
- Episode 37 is not returned by track search or either exact TKKG artist discography. Historical community documentation says it was withheld from the 2018 streaming release. The resolver leaves it unresolved unless a current, verifiable Spotify release is found.
- The previous nine-episode live run on commit \`bdf97a7\` verified episodes 1, 2, 53, 100, 148, 149 and 150. Episodes 20 and 37 remained unresolved.
- The latest live integration run on the current code confirms episodes 1, 2, 53, 100, 148, 149 and 150 are being checked. Episodes 20 and 37 still produce unresolved reports. Episode 20's exact numbered box search and expanded album result pagination do not expose a verifiable album through the current Spotify metadata API. Episode 37 is retained as a negative discovery case because it is absent from the current streaming catalogue. Successful workflow job completion is not counted as successful episode resolution.
- The exact Spotify artist aliases are used as identity checks. Their verified artist IDs are also used as fallback discovery seeds when track search returns no candidates. No arbitrary substring matching is allowed.
- Transient Spotify metadata failures such as a `NoneType` response are retried once before being recorded as unresolved.
- The batch workflow selects inclusive ranges, partitions into bounded jobs, collects unique reports, validates exact coverage, preserves existing verified mappings, and publishes only once from the aggregation job.
- The batch report distinguishes wall-clock runtime from summed per-episode processing time and records configured parallelism and failed batches.
- A dedicated pull-request smoke workflow runs episodes 1 to 6 in two batches of three with two concurrent jobs. A successful earlier run verified all six episodes, with zero unresolved episodes and zero failed batches. Aggregation completed successfully in dry-run mode. It reported 190.42 seconds wall-clock time and 265.83 seconds summed episode-processing time in the latest run. The latest revision repeated both discovery batches successfully; its aggregation job is still running. The canonical catalogue was not modified. The first attempts exposed two shell escaping errors in the workflow itself. Both were fixed before the successful run.

## Test results
- CI at commit \`4800b24\` passed all 97 unit tests.
- The same CI run validated all 243 episodes against schema 1.0.0.
- CI on the latest code commit passed all 100 unit tests and validated all 243 episodes against schema 1.0.0.
- No full 243-episode live discovery run has been started. The controlled batch smoke test must pass before the full range is considered.
- No canonical catalogue files have been modified.
