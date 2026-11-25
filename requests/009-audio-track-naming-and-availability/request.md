# Request 009: Provider track naming and reviewed audio availability

## Background

The latest audio coverage audit exposed three distinct data quality issues. Episode 128 has no usable official provider release available to the user, episode 226 is indexed under a title variant that differs from the catalogue title, and releases beginning around episode 238 use a newer chapter naming convention.

## Desired outcome

Make audio discovery and validation recognise the real provider track structures without changing the source titles or assuming that every episode has the same number of chapters.

## Scope

1. Record episode 128 as reviewed unavailable in `data/audio-unavailable.json`. Preserve the user supplied Spotify album ID `4TdiUT6sWWBMF4nlwGOiC6` as unavailable discovery evidence. The Spotify playlist or album was reported unavailable and its tracks greyed out. This does not independently prove YouTube Music unavailability, so the registry reason must distinguish the observed Spotify evidence from the conclusion that no usable official release could be located on either provider.
2. Add `Der Täter ist unter uns` as an alternate title for episode 226 while retaining the canonical title `Der Täter unter uns`.
3. Recognise `Kapitel NN` as an episode part marker alongside existing `Teil NN` and `Part NN` markers.
4. Keep chapter validation provider specific. Determine each provider's chapter count from its own tracklist. Do not hardcode 20 or require Spotify and YouTube Music to have identical chapter counts.
5. Preserve source track names, order, URLs, album metadata, and provider provenance. Shared intro, summary, opening song, closing song, and outro tracks remain independently classified and included according to the existing selection rules.
6. Re-run discovery and the audio coverage audit for the affected episodes and report what can and cannot be verified.

## Constraints

- Do not remove episode 128 from the catalogue.
- Do not publish the inaccessible Spotify ID as a working album URL.
- Do not infer YouTube Music unavailability solely from Spotify evidence.
- Do not assume every episode from 238 onward necessarily uses the new convention. Detect the actual naming pattern in each provider release.
- Do not impose a fixed chapter count.
- Do not change TKKGDownloader or TKKGTracker in this request.
- Do not merge the implementation branch without explicit approval.

## Acceptance criteria

- The three part markers classify correctly and extract the same numeric part field.
- Numbering validation accepts variable complete sequences such as 1 to 20, 1 to 21, and 1 to 31, and rejects duplicates, gaps, and sequences not starting at 1.
- Spotify and YouTube Music validation remains independent and permits different valid chapter counts.
- Shared track classifications and source metadata are preserved.
- Episode 226 title matching accepts the exact alternate title.
- Episode 128 is excluded from automatic retry only after its reviewed unavailable record is present, while its Spotify ID remains recorded as evidence rather than a usable link.
- Offline tests, catalogue validation, discovery checks, and the coverage audit complete successfully or their blockers are documented.
