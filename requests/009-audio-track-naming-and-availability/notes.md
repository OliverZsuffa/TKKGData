# Implementation notes

Implementation has started on branch `request/009-audio-track-naming-and-availability`.

The Spotify evidence for episode 128 is user supplied: album ID `4TdiUT6sWWBMF4nlwGOiC6`. The user reports that the resource is unavailable and tracks are greyed out. This does not establish the YouTube Music status.

The new chapter convention is not assumed globally by episode number. The parser recognises the marker used in each actual provider tracklist, and chapter counts are derived independently from that provider's numbered tracks.

Actual implementation details and test results will be recorded as work progresses.

## Implemented so far

- Added `Kapitel` to the shared episode part regular expression in `scraper/spotify_structure.py`.
- Updated Spotify title matching and candidate scoring to recognise `Kapitel` as a story part marker.
- Added regression tests for old and new markers, variable chapter counts, independent provider counts, invalid numbering, and episode 226 alias matching.
- Added episode 128 to `data/audio-unavailable.json`, preserving Spotify album ID `4TdiUT6sWWBMF4nlwGOiC6` in the reason and explicitly distinguishing Spotify inaccessibility from YouTube Music status.

## Remaining implementation work

- Add `Der Täter ist unter uns` to episode 226's `alternate_titles` field in `data/episodes.json`. The file is a 7.7 MB catalogue blob and the available GitHub file write operation cannot safely perform a narrow edit without replacing and reformatting the entire catalogue. I am not replacing the whole catalogue merely to change one field.
- Re-run live discovery for episodes 128, 226, 238, and 239 and the full coverage audit.
- Execute the test suite and catalogue validation through CI or a local checkout. The current environment does not provide a GitHub Actions workflow dispatch action or network access for cloning the repository.
