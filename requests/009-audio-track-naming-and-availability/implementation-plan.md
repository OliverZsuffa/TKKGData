# Implementation plan

## Data changes

- Add episode 128 to `data/audio-unavailable.json` with a narrowly worded reason and provenance containing the exact Spotify album ID and the user's report that Spotify marks the release unavailable and its tracks greyed out. Explicitly note that this is not independent evidence about YouTube Music.
- Add `Der Täter ist unter uns` to episode 226's `alternate_titles` array without changing its canonical title.
- Keep the unavailable registry's existing schema version unless a schema change proves necessary.

## Parser and validation

- Extend the shared part marker regular expression in `scraper/spotify_structure.py` to include `kapitel`.
- Ensure every consumer of part markers uses the shared regular expression or equivalent shared helper. In particular, Spotify candidate title matching must recognise chapter labels when deciding whether a title contains a story part.
- Keep numbering validation based on the observed set of part numbers. The expected sequence is 1 through the number of detected parts, not a configured fixed count.
- Keep Spotify and YouTube Music release resolution and validation independent. Each provider's own tracklist establishes its own chapter count and completeness.
- Preserve existing handling for two disc releases with duplicated numbering and for shared tracks.

## Tests

- Add parser tests for Teil, Part, and Kapitel, including case and zero padding.
- Add variable chapter count tests, including counts below and above 20.
- Add rejection tests for duplicate, missing, and non-one-starting numbering.
- Add tests that provider tracklists with different valid chapter counts remain independently valid.
- Add regression tests for shared summary, opening song, closing song, and outro tracks.
- Add title matching coverage for episode 226's alternate title.

## Execution and verification

1. Run all offline unit tests.
2. Run catalogue schema validation.
3. Run targeted discovery for episodes 128, 226, 238, 239, and the remaining audit targets when source access permits.
4. Re-run the full audio coverage audit.
5. Inspect generated diagnostics to ensure inaccessible evidence is not emitted as a playable link.
6. Record test output, audit results, and any live source limitations in `testing.md` and `notes.md`.

## Branch and release

Work on `request/009-audio-track-naming-and-availability`. Create a pull request for review when implementation and tests are complete. Do not merge.
