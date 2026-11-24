# Testing plan

## Migration and preservation

- Snapshot the current catalogue and verify that the snapshot can restore it exactly.
- Run migration against the real current catalogue and representative fixtures.
- Assert every existing YouTube Music track is carried over exactly once, including title, video ID, URL, duration, album association, order, and available provenance.
- Assert every existing Spotify track is carried over exactly once with its available metadata.
- Assert all 14 entries in the Spotify structure override file are represented in episode-level `audio_discovery.spotify` and/or `alternate_titles` data.
- Cover records with both providers, only one provider, incomplete metadata, and legacy paired input. Confirm migration uses the old Spotify fields to construct the independent Spotify list without copying pairing metadata into YouTube Music tracks.
- Assert no `legacy_pairing` field is present in migrated output and that the v2 schema rejects it as an unknown property.
- Confirm canonical episode titles remain unchanged when aliases are added, and all aliases are unique and non-empty.
- Assert no provider data is re-scraped merely to migrate the structure.
- Assert fields whose mapping is ambiguous are reported, not guessed or silently dropped.
- Assert a failed or interrupted migration leaves the canonical catalogue unchanged.
- Assert a failed discovery cannot erase migrated data and a new candidate cannot silently replace existing verified provider data.

## Independent provider validation

- Accept a v2 episode with different Spotify and YouTube Music track counts.
- Reject a provider list whose declared count differs from its own actual list length.
- Reject missing or duplicate provider track IDs and invalid URLs.
- Reject incomplete extraction, null entries, duplicate track numbers, gaps, or reordered entries.
- Validate story part numbering independently from album track numbering.
- Validate recognised extras without requiring a fixed number of extras or story parts.
- Reject wrong artist evidence, wrong episode identity, ambiguous album candidates, and unrelated neighbouring episode tracks.
- Confirm Spotify and YouTube Music search both use episode-level alternate titles and Spotify layout hints without reading an external override file.
- Confirm that different part titles and durations between providers do not cause rejection when both provider lists independently verify.

## Episode fixtures

- Episode 218: complete observed 25-track Spotify and 35-track YouTube Music lists.
- Episode 225: unequal segmentation and complete album extraction.
- Episode 228: compilation handling.
- Episode 236 and 240: larger unequal track lists.
- Episode 150: existing legacy 40-track mapping and compatibility regression.
- Episode 226: Spotify resolution failure remains separately classified.

## Reports and workflows

- Dry-run report presents separate provider lists and their independent verification outcomes.
- Different provider counts are shown clearly and are not reported as a validation error by themselves.
- Failed or ambiguous discovery preserves the current canonical dataset.
- Migration writes the new `audio_release` structure only after the complete catalogue passes validation and every source track is accounted for.
- Full offline tests, schema checks, catalogue validation, compilation, and workflow syntax checks pass.
- Live dry-run results are inspected before enabling any writes.
