# Implementation notes

Implemented on branch `request/009-audio-track-naming-and-availability`.

## Data changes

- Episode 128 remains in the catalogue and is listed in `data/audio-unavailable.json`. Its reason preserves Spotify album ID `4TdiUT6sWWBMF4nlwGOiC6` as evidence only, records the user's report that Spotify marks it unavailable with greyed-out tracks, and records an independent YouTube Music album and playlist search that found no matching release.
- Episode 226 retains canonical title `Der Täter unter uns` and has `Der Täter ist unter uns` in its top-level `alternate_titles` array.
- Independently verified Spotify and YouTube Music releases have been published to `data/episodes.json` for episodes 226, 238, and 239.

## Parser and validation changes

- `scraper/spotify_structure.py` recognises `Kapitel NN` alongside `Teil NN` and `Part NN`.
- Spotify candidate matching and scoring recognise `Kapitel` markers, and Spotify search now also includes a `Kapitel 01` query.
- YouTube Music track search uses the chapter label found in the Spotify track title when constructing its episode query.
- Chapter numbering is derived from each provider's actual tracklist. No fixed chapter count is imposed and Spotify and YouTube Music remain independent.
- Existing shared-track selection continues to retain summaries, intros, opening songs, closing songs, and outros.

## Published provider results

| Episode | Spotify tracks | YouTube Music tracks | Spotify chapters | YouTube Music chapters |
|---|---:|---:|---:|---:|
| 226 | 25 | 47 | 21 | 43 |
| 238 | 24 | 45 | 20 | 41 |
| 239 | 24 | 44 | 20 | 40 |

All six provider tracklists were independently verified and stored in the episode records. The YouTube Music album tracklists were verified even though separate playlist IDs were unavailable.

## Automated verification

- 150 unit tests passed.
- All 243 catalogue episodes passed catalogue validation.
- The post-publication audio coverage audit reports episodes 240, 241, 242, and 243 as needing investigation.
- Known unavailable episodes are 19, 20, 37, and 128.

## Episode 128 provider review

The exact Spotify album ID supplied by the user remains in the unavailable reason and is not exposed as a working link. An independent YouTube Music search returned no matching album or playlist. The unavailable classification is therefore based on both provider checks, not inferred from Spotify alone.
