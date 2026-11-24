# Implementation notes

Plan documentation only. No discovery code, schema, catalogue data, workflow, or consumer behaviour has been changed.

## Preservation baseline

- Base branch: `main`
- Base commit: `3d060d3483a2a4def150c3356e8cbf9ab52ea19e`
- The existing `audio_release` structure may be replaced by independent Spotify and YouTube Music lists.
- All previously scraped provider data must be migrated into the new structure, especially the existing YouTube Music tracks.
- The implementation must create a recoverable snapshot and prove that every source track is accounted for before publishing.
- No catalogue records or existing verified mappings have been modified by this planning change.

Implementation and test results will be recorded here after explicit approval.
