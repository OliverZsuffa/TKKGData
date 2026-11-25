# Testing plan and results

## Automated checks

- [x] Part marker classification for Teil, Part, and Kapitel.
- [x] Variable chapter counts of 12, 20, 21, and 31.
- [x] Rejection of duplicate, missing, and non-one-starting chapter numbers.
- [x] Independent provider chapter counts, including Spotify with 20 and YouTube Music with 21 chapters.
- [x] Shared summary, intro, opening song, closing song, and outro selection regression coverage.
- [x] Episode 226 alternate title matching and catalogue storage.
- [x] Episode 128 unavailable registry validation and discovery exclusion, including a regression test that confirms no provider request is attempted.
- [x] Full offline unit test suite: **151 tests passed** (latest CI run pending after the additional registry regression test)..
- [x] Catalogue validation: **243 episodes passed**.
- [x] Verified releases for episodes 226, 238, and 239 written to the catalogue and validated.
- [x] Post-publication coverage audit: episodes 240, 241, 242, and 243 remain under investigation.

## Live checks

- [x] Episode 128 Spotify album ID recorded as unavailable evidence, not a playable link.
- [x] Episode 128 YouTube Music independently checked. No matching album or playlist was found.
- [x] Episode 226 Spotify and YouTube Music release discovery and verification.
- [x] Episode 238 and 239 new chapter naming discovery and verification.
- [x] Full audio coverage audit after publishing the verified releases.

## Provider chapter counts

| Episode | Spotify | YouTube Music |
|---|---:|---:|
| 226 | 21 | 43 |
| 238 | 20 | 41 |
| 239 | 20 | 40 |
