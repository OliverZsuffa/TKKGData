# Implementation notes

## Status
The approved implementation is on the Request 006 branch. No canonical catalogue data has been changed or published. The pull request remains unmerged.

## Investigation findings
- The original resolver used one Spotify search result and required the artist credit to be exactly \`TKKG\`.
- Historical tracks use both \`TKKG\` and \`TKKG Retro-Archiv\` artist credits. The verified Spotify artist IDs are kept in an explicit alias map, not inferred from arbitrary artist names.
- The free spotDL Spotify client does not expose album-name search. Historical compilation discovery therefore uses SpotAPI's public album search and paginated artist discographies, followed by full album metadata validation.
- Episode 20 is listed in Spotify's public catalogue as track 1 on disc 2 of \`07/3er Box - Folge 19-21\`. The Spotify listing identifies three full-episode tracks and includes the exact episode title: https://open.spotify.com/intl-de/album/0f3YoQoLsSQbXI8Cp34lR2
- Episode 37 is not currently returned by track search or either exact TKKG artist discography. Historical community documentation says episode 37 was withheld from the 2018 streaming release. The resolver must leave it unresolved unless a current, verifiable Spotify release is found. It must not substitute an unrelated recording or infer a track.
- The original nine-episode live integration run on commit \`bdf97a7\` verified episodes 1, 2, 53, 100, 148, 149 and 150. Episodes 20 and 37 remained unresolved. This run predates the new direct album-search fallback and is not evidence for the latest code.
- The new album-search fallback specifically searches the episode title and calculated three-episode box range, then verifies the selected track against the fetched album tracklist.
- The batch workflow selects inclusive ranges, runs bounded matrix jobs, downloads every report, validates exact coverage, and publishes only once from the aggregation job. Existing verified mappings are preserved.
- SpotAPI is pinned in \`requirements-audio.txt\` because the resolver now uses its public Spotify metadata search and artist catalogue methods.

## Test results
- The previous branch validation run passed the unit tests and full 243-episode catalogue validation at commit \`bdf97a7\`.
- The previous live integration run covered nine episodes with seven verified and two unresolved, as listed above.
- The latest album-search helper has a dedicated mocked regression test. A fresh CI run against the latest commit is still required before merge.
- No full 243-episode live discovery run has been started. It must first be run as a dry run, with bounded parallelism, and reviewed before any write-enabled publication.
