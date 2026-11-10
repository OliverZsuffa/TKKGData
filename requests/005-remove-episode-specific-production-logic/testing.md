# Testing plan

## Automated tests
1. Run `python -m unittest discover -s tests -v`.
   Expected: all existing tests and new metadata adapter and diagnostic tests pass.
2. Run Python compilation for all remaining scraper modules.
   Expected: no syntax errors.
3. Validate the catalogue using the repository's validation command.
   Expected: all episode records and existing verified mappings remain valid.
4. Parse the workflow YAML.
   Expected: valid syntax, scheduled and manual triggers present, no push-only special path, no FFmpeg install, and no experiment steps.
5. Search production Python, workflow files, README, and current knowledge docs for fixed episode identifiers, playlist IDs, and deleted experiment references.
   Expected: no production matches. Episode-specific test fixtures and historical request records may remain.
6. Inspect dependency imports and installation requirements.
   Expected: no FFmpeg or audio processing dependency is required by metadata discovery.

## Spotify metadata adapter
- Resolve the first track for a known episode and validate its Spotify artist, exact normalized title, and album ID.
- Retrieve the album tracklist and validate album identity, track numbers, track IDs, titles, and durations.
- Run with FFmpeg absent from PATH and verify no subprocess tries to invoke it.
- Test malformed, empty, and incomplete metadata responses.
- Confirm no new credentials or repository secrets are required unless explicitly approved.

## Episode number to verified links integration matrix
Run each episode separately through the normal path with only its episode number supplied. Do not pass a playlist ID for episode 150 during the automatic discovery test.

| Episode | Purpose | Required result |
|---|---|---|
| 148 | Independent coverage episode | Resolve Spotify album and ordered track links, then discover and verify the matching YouTube Music album or playlist page and all ordered song links. Record any unresolved stage precisely. |
| 149 | Previous failure case, `Tims gefährlichster Gegner` | Re-run the exact discovery path. Either verify the complete playlist and ordered links, or produce actionable playlist and song candidate diagnostics. No silent fallback failure. |
| 150 | Known positive control, `Heiße Nächte im Dezember` | Automatically rediscover the known playlist without a hardcoded or manually supplied playlist ID, then verify all 40 ordered mappings and link targets. |

For every episode, capture the Spotify album URL, all Spotify track URLs, the YouTube Music playlist URL, all YouTube Music song/video URLs, expected and discovered track counts, order and duration checks, verification result, and stage timings. Candidate URLs that fail verification must be labelled as unverified and must not be published as canonical mappings. Run with writes disabled during these discovery tests.

A successful test means the full episode-number-to-links chain is verified. An episode that remains unresolved is still useful diagnostic coverage, but it is not a passing end-to-end test.

## YouTube Music matching diagnostics
- A failed playlist lookup remains present in the final episode report when individual song fallback also fails.
- Candidate diagnostics record only bounded relevant fields and identify why a candidate did not meet the threshold.
- Existing matching score threshold and ambiguity behaviour remain unchanged.
- A successful exact ordered playlist still produces the same verified ordered mappings.
- Automatic playlist discovery succeeds for episode 150 without its known playlist ID being supplied.
- The three live episode runs produce separate, inspectable reports. The final summary distinguishes end-to-end successes from unresolved diagnostic cases.
- A zero-match run emits a visible workflow warning and summary with zero verified and the correct unresolved count.

## Workflow behaviour
- Manual dispatch with no episode processes missing mappings within the configured limit.
- Manual dispatch with an episode selects that episode.
- A supplied playlist ID is accepted only with one explicitly selected episode.
- Manual writes remain opt-in.
- Scheduled runs select latest missing mappings and write verified results.
- No workflow step installs FFmpeg or runs the removed experiment script.

## Performance measurement
- Capture durations for setup, dependency installation, Spotify metadata resolution, YouTube Music search and verification, and total job runtime.
- Compare the new run against run 42815546600.
- Confirm the FFmpeg installation stage is absent and report the measured runtime. Do not assert an unmeasured speedup.
