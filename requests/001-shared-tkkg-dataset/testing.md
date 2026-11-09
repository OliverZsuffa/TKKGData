# Testing plan: Request 001

**Status:** Planned only. No implementation or test execution has started.

## Repository foundation
1. Clone the repository and follow the documented setup instructions.
   Expected: clean setup works on a supported Python version without private credentials.
2. Run the documented offline validation command against the committed dataset.
   Expected: it completes without network access and validates schema and relationships.
3. Run the test suite.
   Expected: deterministic tests pass without contacting external providers.

## Dataset migration
1. Compare the migrated dataset with the current TKKGtracker catalogue.
   Expected: all valid episode identities and existing sourced metadata are accounted for, with additions, removals, and conflicts explained in a migration report.
2. Inspect episodes with incomplete or conflicting source metadata.
   Expected: unknown values remain unknown and source provenance is retained.
3. Validate all stable IDs and relationships.
   Expected: duplicate IDs, broken references, malformed URLs, and invalid numbering are rejected.

## Audio release mapping
1. Validate episode 150 against saved Spotify and YouTube Music evidence.
   Expected: the dataset contains the verified album and playlist mapping plus individual song URLs where confirmed.
2. Test a provider summary count that disagrees with actual returned track records.
   Expected: the validated record count determines the expected count.
3. Test missing, duplicate, reordered, ambiguous, and mismatched tracks.
   Expected: no incomplete or ambiguous mapping is published as verified.
4. Simulate a provider outage after a mapping has been verified.
   Expected: the previous verified mapping remains unchanged.
5. Test an episode with no YouTube Music playlist but with individually verified songs.
   Expected: song URLs can be stored without inventing a playlist mapping.

## Publication
1. Validate a candidate dataset with CI.
   Expected: invalid data blocks publication and leaves the last valid version available.
2. Publish a versioned snapshot.
   Expected: the immutable URL remains tied to that dataset version.
3. Retrieve the stable latest URL and a versioned URL.
   Expected: both return valid JSON with declared schema and dataset versions.

## TKKGTracker consumer
1. Load the app online using the TKKGData dataset.
   Expected: episode list and metadata render correctly.
2. Refresh after a new version is published.
   Expected: new metadata appears without resetting local progress.
3. Load offline after a successful online load.
   Expected: the last valid dataset and user progress remain available.
4. Serve malformed or incompatible JSON.
   Expected: the tracker rejects it and retains the last-known-good snapshot.

## TKKGDownloader consumer
1. Request one episode with a verified provider mapping.
   Expected: metadata and exact source URLs are read from TKKGData without a new source search.
2. Request an episode with no verified audio mapping.
   Expected: the downloader reports the missing mapping and follows only the approved fallback behaviour.
3. Download a known episode and a short range on Windows.
   Expected: correct tracks are selected and merged into one MP3 per episode.
4. Test overwrite protection and --overwrite.
   Expected: existing outputs are protected by default and replaced only when requested.

## Cross-repository regression
1. Compare tracker and downloader episode titles for the same episode.
   Expected: both use the same TKKGData record.
2. Compare the provider release and track list selected by the downloader with the published dataset.
   Expected: IDs and ordering match exactly.
3. Verify no consumer scraper or duplicate authoritative episode dataset remains after cutover.
   Expected: source discovery and shared data maintenance exist only in TKKGData.

## Actual observations
Oliver's real-device and Windows observations should be recorded here or in notes.md without replacing earlier observations.
