# Testing plan and results

## Automated checks

- [x] Part marker classification for Teil, Part, and Kapitel.
- [x] Variable chapter counts of 12, 20, 21, and 31.
- [x] Rejection of duplicate, missing, and non-one-starting chapter numbers.
- [x] Independent provider chapter counts, including Spotify with 20 and YouTube Music with 21 chapters.
- [x] Existing shared track classification and inclusion regression tests.
- [x] Episode 226 alternate title matching.
- [x] Episode 128 unavailable registry entry recorded with its Spotify evidence.
- [x] Full offline unit test suite: **150 tests passed**.
- [x] Catalogue validation: **243 episodes passed**.
- [x] Explicit assertion that episode 226 contains `Der Täter ist unter uns` in `alternate_titles`.

## Live checks

- [ ] Episode 128 Spotify ID and unavailable status checked without exposing it as a playable link.
- [ ] Episode 128 YouTube Music checked independently.
- [ ] Episode 226 Spotify and YouTube Music discovery.
- [ ] Episode 238 and 239 chapter format discovery.
- [ ] Full audio coverage audit.

Live discovery and audit are being run in GitHub Actions. Results will be added here once the workflow finishes.
