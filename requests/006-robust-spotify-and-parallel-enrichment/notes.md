# Implementation notes

## Status
Request 006 is implemented on the feature branch and pull request #15 is open. Automated validation, representative live discovery, and the controlled parallel batch smoke test passed. No canonical catalogue files have been changed or published.

## Spotify resolution findings
- The original resolver used one Spotify search result and required the artist credit to be exactly \`TKKG\`.
- Historical releases use both \`TKKG\` and \`TKKG Retro-Archiv\`. Exact verified artist names and IDs are used. Arbitrary substring matches are rejected.
- The free spotDL Spotify client does not expose album-name search. The resolver now searches Spotify's public album catalogue, including top results, exact numbered three-episode box titles, and paginated results. It also checks the exact artists' album and compilation discographies.
- Transient Spotify metadata failures such as a \`NoneType\` response are retried once.
- A public Spotify page is indexed for \`07/3er Box - Folge 19-21\`: https://open.spotify.com/intl-de/album/0f3YoQoLsSQbXI8Cp34lR2. The current German-market Spotify metadata API and exact artist discographies do not return that album or its tracks. It is not safe to publish an unverified episode 20 mapping.
- Episode 37 is not returned by track search, album search, or either exact TKKG artist discography. It remains unresolved unless a current verifiable Spotify release is found.

## Live integration results
The final representative integration run checked nine episodes:
- Verified: 1, 2, 53, 100, 148, 149, 150.
- Unresolved: 20, 37.
- Episodes 1, 2 and 53 each had 25 Spotify and 25 YouTube Music tracks verified.
- Episodes 100, 148, 149 and 150 each had 40 Spotify and 40 YouTube Music tracks verified.
- No unverified mappings were generated. Successful job completion is not treated as successful episode resolution.

## Parallel batch smoke test
The pull-request smoke workflow processed episodes 1 to 6 in two batches of three, with two concurrent workers.
- 6 verified, 0 unresolved, 0 failed batches.
- Aggregation validated both batch reports and completed in dry-run mode.
- Wall-clock runtime: 190.42 seconds.
- Summed episode-processing time: 265.83 seconds.
- The canonical catalogue remained unchanged.

## Automated validation
- 100 unit tests passed.
- All 243 episodes passed catalogue schema validation.
- Tests cover historical artist aliases, compilation album selection, transient retries, inclusive range selection, exact batch coverage, duplicate assignment rejection, dry-run safety, preservation of existing verified mappings, and publication blocking on failed batches.

## Remaining operational step
No full 243-episode live discovery run has been started. The manual workflow supports inclusive ranges, bounded batches, configurable parallelism, dry-run reports, and a single safe publication step. The full catalogue run should first be launched in dry-run mode and reviewed before enabling writes.
