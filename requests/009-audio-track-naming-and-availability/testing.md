# Testing plan and results

## Planned automated checks

- [x] Part marker classification tests added for Teil, Part, and Kapitel. Execution is pending CI.

- [x] Variable chapter count tests added for 12, 20, 21, and 31. Execution is pending CI.

- [x] Duplicate, gap, and invalid starting number rejection tests added. Execution is pending CI.

- [x] Independent Spotify and YouTube Music count test added for 20 versus 21 chapters. Execution is pending CI.

- [ ] Shared track classification and inclusion regression.
- [x] Unit test added for matching the exact alternate title when supplied on the episode object. The catalogue record update remains pending.

- [ ] Episode 128 unavailable registry validation and retry exclusion.
- [ ] Full offline unit test suite.
- [ ] Catalogue validation.
- [ ] Audio coverage audit.

## Planned live checks

- [ ] Episode 128 Spotify ID checked without treating the unavailable resource as playable.
- [ ] Episode 128 YouTube Music independently checked.
- [ ] Episode 226 Spotify and YouTube Music discovery.
- [ ] Episode 238 and 239 chapter format discovery.
- [ ] Remaining affected audit targets checked.

## Results

Implementation and execution results will be added here after the checks have actually run.
