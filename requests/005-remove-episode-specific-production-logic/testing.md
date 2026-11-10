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

## YouTube Music matching diagnostics
- A failed playlist lookup remains present in the final episode report when individual song fallback also fails.
- Candidate diagnostics record only bounded relevant fields and identify why a candidate did not meet the threshold.
- Existing matching score threshold and ambiguity behaviour remain unchanged.
- A successful exact ordered playlist still produces the same verified ordered mappings.
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
