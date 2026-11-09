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
Pending the next CI run and the episode 150 dry-run workflow after merge.
