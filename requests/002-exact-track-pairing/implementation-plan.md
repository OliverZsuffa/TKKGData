# Implementation plan: Exact Spotify and YouTube Music track pairing

**Status:** Approved. Implementation in progress.

1. Inspect the Spotify track records returned by spotDL. Use the existing song_id and url fields.
2. Validate the Spotify track ID format and canonical URL. If one is absent, derive it from the other only when the available value is valid.
3. Reject records where the ID and URL disagree or both are unavailable.
4. Store spotify_track_id and spotify_track_url in every verified YouTube Music track object.
5. Add both fields to the JSON Schema required list.
6. Extend catalogue validation to check the Spotify track ID against the URL path.
7. Update fixtures and tests for valid pairing and invalid Spotify identity.
8. Update the audio source knowledge note and downloader contract.
9. Run the full offline test suite and validate the existing dataset.
10. Do not modify existing published audio mappings until a new enrichment run verifies the expanded record shape.
