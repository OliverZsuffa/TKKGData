# Testing plan: Request 002

1. Resolve a Spotify track record with valid song_id and url.
   Expected: the exact Spotify track ID and URL are stored with the matched YouTube Music song.
2. Resolve a record with valid URL but no song_id.
   Expected: the ID is derived from the URL.
3. Resolve a record with valid song_id but no URL.
   Expected: the canonical URL is derived from the ID.
4. Resolve a record with malformed ID or URL.
   Expected: the episode mapping is rejected.
5. Resolve a record whose ID and URL disagree.
   Expected: the episode mapping is rejected.
6. Validate a complete audio_release fixture.
   Expected: schema and cross-provider validation pass.
7. Run python -m unittest discover -s tests -v.
   Expected: all tests pass.
8. Validate data/episodes.json.
   Expected: all current episode records remain valid. Existing mappings without Spotify track-level IDs are not rewritten.
