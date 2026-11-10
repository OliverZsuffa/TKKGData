# Implementation plan

## 1. Production diagnostic script
- Remove the fixed episode object and default playlist ID.
- Add a catalogue loader that reads the canonical episode JSON and resolves the requested number.
- Require `--episode`; reject numbers that are absent from the catalogue.
- Keep `--playlist-id` optional and pass it only to the playlist extraction experiment.
- Build album, playlist, and song search queries from the selected episode's number and title.
- Include the selected episode record in the report.
- Keep the existing bounded diagnostic behaviour and output path.

## 2. GitHub Actions workflow
- Remove the push trigger and all push-event special handling, since it exists only to rerun the fixed episode experiment.
- Leave the scheduled workflow as a generic latest-first batch that writes verified results.
- Set the manual episode input default to an empty string.
- Add an optional manual playlist ID input.
- Pass the optional playlist ID to the normal enrichment command only when a single episode is selected.
- Run the alternate diagnostic script on manual dispatch only when an episode is explicitly selected. Pass the same episode and optional playlist ID.
- Upload the diagnostic report for that selected-episode run.
- Keep manual writes opt-in and scheduled writes enabled.

## 3. Current documentation
- Update README examples to use a generic episode placeholder and explain how to select a real catalogue episode.
- Update the audio-source knowledge page to describe generic discovery and optional explicit playlist recovery.
- Describe current coverage numerically without naming an individual episode as special.
- Leave historical request documentation untouched so the development history remains auditable.

## 4. Regression protection
- Keep existing episode 150 test fixtures and their test-only references.
- Add tests for diagnostic catalogue lookup, missing episode rejection, dynamic query construction, and optional playlist handling.
- Add workflow-level checks or static assertions to ensure the manual input has no episode default and production workflow content has no fixed episode identifier or playlist ID.

## 5. Verification
- Run the complete unittest suite.
- Run Python compilation for the scraper modules.
- Validate the canonical catalogue and generated exports.
- Parse or lint the workflow YAML.
- Search production Python, workflow files, README, and current knowledge documentation for the former episode-specific number, title, and playlist ID. Test fixtures and historical request records are expected exceptions.
- Confirm the workflow still has a scheduled trigger and manual dispatch, and that scheduled writes and manual opt-in writes behave as intended.
