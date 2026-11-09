# Testing plan: Request 004

1. Verify a two-track mocked playlist whose titles differ only by punctuation.
   Expected: both tracks match in order and produce exact Spotify and YouTube Music URLs.
2. Swap the playlist entries.
   Expected: reject the first mismatched track.
3. Use a playlist with the wrong count.
   Expected: reject it.
4. Use an invalid video ID.
   Expected: reject it.
5. Use a duration difference above eight seconds.
   Expected: reject it.
6. Use an episode title that does not match the playlist title.
   Expected: reject it.
7. Run discover_episode_audio with a valid explicit playlist.
   Expected: it uses playlist entries and does not invoke individual song search.
8. Run the full offline test suite and validate the existing dataset.
   Expected: all tests pass and no existing audio mapping is rewritten.
9. Run the episode 150 workflow dry run.
   Expected: all 40 Spotify tracks match the official YouTube Music playlist, with no audio download and no dataset write.
