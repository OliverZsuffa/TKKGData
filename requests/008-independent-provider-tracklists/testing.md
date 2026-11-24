# Testing plan

## Legacy compatibility and preservation

- Load representative existing `audio_release` fixtures and validate them with the unchanged v1 rules.
- Assert the exact legacy JSON values and serialization remain unchanged after loading and saving a catalogue containing v2 data.
- Assert a v2 discovery failure leaves any existing v1 object untouched.
- Assert a new v2 result can coexist with a legacy v1 object without modifying it.
- Assert a conflicting new result cannot silently replace an existing verified v2 object.
- Assert an interrupted or invalid write does not replace the canonical catalogue file.

## Independent provider validation

- Accept a v2 episode with different Spotify and YouTube Music track counts.
- Reject a provider list whose declared count differs from its own actual list length.
- Reject missing or duplicate provider track IDs and invalid URLs.
- Reject incomplete extraction, null entries, duplicate track numbers, gaps, or reordered entries.
- Validate story part numbering independently from album track numbering.
- Validate recognised extras without requiring a fixed number of extras or story parts.
- Reject wrong artist evidence, wrong episode identity, ambiguous album candidates, and unrelated neighbouring episode tracks.
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
- Write mode updates only the new v2 field for the selected episode after complete verification.
- Full offline tests, schema checks, catalogue validation, compilation, and workflow syntax checks pass.
- Live dry-run results are inspected before enabling any writes.
