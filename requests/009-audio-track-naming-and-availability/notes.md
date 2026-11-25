# Implementation notes

Implemented on branch `request/009-audio-track-naming-and-availability`.

## Data changes

- Episode 128 is present in `data/audio-unavailable.json`. Its reason preserves the user supplied Spotify album ID `4TdiUT6sWWBMF4nlwGOiC6` and reports the unavailable Spotify resource and greyed-out tracks. It explicitly does not infer YouTube Music unavailability from that Spotify evidence.
- Episode 226 retains canonical title `Der Täter unter uns` and now has `Der Täter ist unter uns` in its top-level `alternate_titles` array in `data/episodes.json`.

## Parser and validation changes

- `scraper/spotify_structure.py` recognises `Kapitel NN` alongside `Teil NN` and `Part NN`.
- Spotify candidate matching and scoring recognise `Kapitel` part markers.
- Existing numbering validation derives the expected sequence from the number of detected parts. It has no fixed 20 chapter limit and validates each provider tracklist independently.
- Existing shared-track selection continues to retain summary, intro, opening song, closing song, and outro tracks.

## Automated verification

A temporary GitHub Actions workflow completed successfully and removed itself after applying the large catalogue file update.

- 150 unit tests passed.
- All 243 catalogue episodes passed catalogue validation.
- Episode 226's alternate title was explicitly asserted in the validation step.

## Live verification

Targeted live discovery for episodes 128, 226, 238, and 239 and the full audio coverage audit are running in a temporary GitHub Actions workflow. Their results will be recorded after completion.
