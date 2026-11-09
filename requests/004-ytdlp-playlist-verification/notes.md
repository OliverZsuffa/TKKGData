# Notes: Request 004

## Evidence
Audio source experiment artifact from workflow run 42700291218:
- yt-dlp extracted the official OLAK playlist successfully.
- Playlist title: Album - 150/Heiße Nächte im Dezember.
- Playlist count and extracted entry count: 40.
- Spotify album actual track record count: 40.
- First playlist entry: 150 - Heiße Nächte im Dezember (Teil 01).
- First Spotify track: 150 - Heiße Nächte im Dezember - Teil 01.
- The observed title differences are punctuation only, and sampled durations differ by about one second.

## Implementation
- Added yt-dlp flat playlist extraction for explicit playlist IDs.
- Added exact ordered title matching and duration tolerance.
- Added individual Spotify and YouTube Music URL pairing from the playlist entries.
- Reordered discovery to prefer a fully verified playlist before song search.
- Updated the push-triggered episode 150 dry run to pass the known official playlist ID.
- Made the alternate diagnostic experiment non-blocking.

## Test results

- PR #5 was merged into main as commit f229e4c2d64c31b1c8549144e1dc4a01442a5256.
- GitHub Actions validation run 42708617467 passed the complete Python unit test suite and validated all 243 published episode records against the schema.
- The post-merge TKKGData dataset refresh completed successfully in run 42708728320.
- The post-merge episode 150 dry-run is running in workflow run 42708728228. It uses the explicit official playlist ID and does not write to the catalogue.

The 40-track live match acceptance criterion remains pending until the dry-run report is inspected.
