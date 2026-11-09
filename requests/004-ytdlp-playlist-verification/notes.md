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
- The post-merge episode 150 dry-run completed successfully in workflow run 42708728228. Its artifact report confirms:
- Dry-run mode, with no catalogue write.
- One target episode, one verified result, and zero failures.
- Spotify album track count: 40.
- Official YouTube Music playlist ID: OLAK5uy_mQRbJNANh1H4CKbmM5ez5LSW1HJFvE3QI.
- YouTube Music playlist entries: 40.
- All 40 track numbers contiguous and ordered.
- All 40 Spotify track IDs and YouTube video IDs valid and consistent with their URLs.
- All 40 titles match after conservative punctuation normalization.
- Duration evidence was present and within the eight-second tolerance for all tracks.

The independent diagnostic artifact also confirms yt-dlp extracts the same 40-entry playlist from both music.youtube.com and www.youtube.com. Individual YouTube Music song search returned no exact matches, which validates the decision to use direct playlist extraction as the primary method.

The verified mapping was published to TKKGData in commit 2233bfd68fc832897a5f916deb9abb24282d9b08. The write workflow used the latest main checkout, revalidated the full 40-track mapping, and committed episodes.json, episodes.csv, dataset-metadata.json, and scrape-report.json. The published dataset still contains 243 episodes, and episode 150 now has a verified Spotify album, YouTube Music playlist, and 40 individual cross-provider track pairs.
