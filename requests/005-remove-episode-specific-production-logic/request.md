# Request 005: Remove episode-specific production logic

## Status
Planning only. Awaiting approval.

## Context
Episode numbers are ordinary catalogue data. The production scraper, diagnostic tools, and automation must not contain special handling for any individual episode. Episode 150 may remain explicitly represented in regression tests and test fixtures, but must not be referenced as a special case in production code, workflow configuration, or current operational documentation.

The current implementation contains episode-specific assumptions in the audio source experiment script and the audio enrichment workflow. The manual workflow also defaults to one particular episode, and push-triggered logic supplies a fixed playlist and special commit marker.

## Desired outcome
All production discovery and diagnostics operate on the episode selected by the user or by the generic batch-selection rules. No episode number or provider playlist is privileged.

## Scope
- Generalize `scraper/audio_source_experiments.py` to load the selected episode from the canonical catalogue and derive search queries from its number and title.
- Require an explicit episode selection for the diagnostic script. Keep an optional explicit playlist ID as a user-supplied diagnostic override, not a default.
- Make the workflow manual episode input empty by default and add an optional playlist ID input for explicit recovery.
- Remove fixed-episode push handling, fixed playlist injection, and episode-specific commit markers from the workflow. Keep scheduled enrichment and manual dispatch.
- Run the diagnostic experiment for any manually selected episode, using the same selected episode and optional playlist override.
- Update current README and knowledge documentation so they explain generic behaviour without presenting one episode as a production example or special case.
- Keep historical request records and actual catalogue data intact. Episode 150 references in tests and test fixtures are allowed and should remain as regression coverage.

## Out of scope
- Changing matching or verification rules.
- Changing the catalogue schema or published episode records.
- Removing regression tests or rewriting their fixture data.
- Changing TKKGTracker or TKKGDownloader.

## Acceptance criteria
1. No production Python source or workflow file contains a hardcoded episode number, title, or playlist ID for a particular episode.
2. The diagnostic script accepts any valid episode present in the catalogue and derives all episode-specific queries from that record.
3. An explicitly supplied playlist ID is used only for the explicitly selected episode and is never silently applied to other episodes.
4. Manual workflow dispatch has no episode-specific default.
5. Scheduled enrichment continues to process up to its configured limit of missing mappings and publish only verified results.
6. Manual dispatch can run one selected episode or a bounded batch, with optional explicit playlist override for one selected episode.
7. Episode-specific regression fixtures remain in tests.
8. Offline tests, workflow syntax checks, and catalogue validation pass.
