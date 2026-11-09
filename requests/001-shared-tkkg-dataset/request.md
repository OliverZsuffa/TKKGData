# Request 001: Establish TKKGData as the shared TKKG dataset

## Status
Awaiting approval. Planning only. No scraper, schema, consumer, or application implementation is authorized yet.

## Desired outcome
Make TKKGData the single source of truth for structured TKKG episode information and all verified release/source mappings. TKKGData discovers, scrapes, reconciles, validates, and publishes the dataset. TKKGTracker and TKKGDownloader consume that published data and do not maintain independent episode catalogues or scrape source websites.

The dataset should be useful independently of either application and should support future TKKG tools.

## Context
The current responsibilities are split incorrectly:
- TKKGtracker contains the episode scraper, catalogue schema, generated episode JSON/CSV, source-link extraction, and shared audio enrichment work.
- TKKGDownloader downloads and merges audio, but currently retrieves episode metadata from TKKGtracker and resolves Spotify releases itself.
- TKKGData has been created as a new repository to become the dedicated data project.

TKKGtracker request 009 explored Spotify and YouTube Music enrichment. It is now superseded as an architectural direction by this three-repository split. Its useful research, fixtures, validation rules, and implementation work should be reviewed and migrated into TKKGData rather than duplicated.

Important existing findings:
- TKKGtracker currently publishes data/episodes.json and data/episodes.csv.
- TKKGtracker has source adapters for the official TKKG catalogue and historical archive, with source coverage and access restrictions documented in its knowledge base.
- Episode 150 has a known Spotify album and official YouTube Music playlist. Prior Spotify metadata returned 40 track records despite an inconsistent summary track count. Actual validated records, not the provider summary count, must determine the expected number of tracks.
- Audio discovery has explored both playlist matching and individual YouTube Music song URLs. The intended dataset should store both when verified.
- TKKGDownloader's current spotDL workflow has difficulty matching some audio tracks through text search. Verified source mappings should allow the downloader to avoid rediscovering the same metadata independently.

## Required behaviour
1. TKKGData owns the canonical episode dataset, schema, source adapters, scraping, enrichment, validation, reporting, and publication.
2. The initial migration preserves the existing regular main-series episode catalogue and its verified metadata. Scope expansion to Junior, film tie-ins, live albums, calendars, or unrelated releases must be explicit and evidence based.
3. The dataset can represent episode identity, titles and aliases, release information, synopses, cast and production metadata, archive chapter information, digital releases, provider albums/playlists, provider tracks, official listening links, source provenance, and verification status where evidence exists.
4. Multiple editions and releases may refer to one episode. The model must not assume one Spotify album or one YouTube Music playlist per episode.
5. YouTube Music data must support both a verified playlist URL and verified individual song URLs. Spotify data must include the album and its actual returned track records where available.
6. Archive chapter segmentation and streaming release track divisions are separate concepts and must never be conflated.
7. Published data contains verified facts only. Candidates and unresolved conflicts belong in discovery reports or reviewable candidate files, not in consumer-facing verified fields.
8. TKKGTracker consumes the published dataset. It retains only app presentation, local listening progress, ratings, notes, favourites, and user preferences.
9. TKKGDownloader consumes the published dataset. It retains only download execution, local output management, and download-specific preferences. It must not independently scrape episode sources or rediscover verified album mappings.
10. Both consumers handle dataset versioning, schema compatibility, temporary network failure, and last-known-good data according to their runtime needs.
11. The dataset is accessible through a stable documented URL and immutable versioned snapshots.
12. Source failures must not erase previously verified facts or prevent unrelated valid records from being published.
13. The repository has the standard request system, project instructions, README, documentation index, knowledge base, approved decisions log, and automated validation workflow.

## Scope

### Included
- Establish TKKGData repository development infrastructure and request workflow.
- Inventory current TKKGtracker data, schema, scraper, source adapters, tests, knowledge, and request 009 work.
- Define a versioned canonical data model and JSON Schema.
- Migrate source discovery and scraping responsibilities from TKKGtracker into TKKGData.
- Migrate and improve audio release enrichment, including Spotify album metadata, YouTube Music playlists, and individual YouTube Music song URLs.
- Preserve source provenance, retrieval timestamps, verification status, and structured diagnostics.
- Define deterministic merge, conflict, correction, and preservation rules.
- Add fixture-based tests, schema validation, catalogue consistency checks, and CI.
- Publish a stable latest dataset and immutable versioned snapshots.
- Define a documented consumer contract and migration sequence for TKKGTracker and TKKGDownloader.
- Keep the three repositories' request plans coordinated.

### Not included
- Implementing TKKGTracker UI or progress-storage changes in this repository.
- Implementing TKKGDownloader download or merge behaviour in this repository.
- Storing audio files or serving audio content.
- User accounts, cloud progress synchronization, or personal preferences.
- Bypassing authentication, robots.txt, source terms, rate limits, or access restrictions.
- Claiming full TKKG franchise coverage before sources and scope are explicitly defined.
- Rewriting all historical data without an audit and preservation strategy.

## Acceptance criteria
- [ ] TKKGData has a documented, versioned schema and a reproducible generated dataset.
- [ ] The canonical dataset preserves all valid existing TKKGtracker episode records and their provenance during migration.
- [ ] The data model distinguishes episodes, releases, provider albums/playlists, provider tracks, and archive chapters.
- [ ] The model supports multiple releases per episode and records both YouTube Music playlist and individual track URLs when verified.
- [ ] Candidate discovery and verified published data are separate.
- [ ] Validation catches malformed IDs and URLs, duplicate identities, invalid ordering, contradictory track counts, and broken relationships.
- [ ] Failed or ambiguous enrichment never overwrites verified mappings.
- [ ] Episode 150 is represented by a regression fixture using actual returned Spotify track records and independently verified YouTube Music playlist and song results. No production logic hardcodes 40 tracks.
- [ ] Scraping is bounded, cached, paced, source-aware, and respectful of access restrictions.
- [ ] CI validates schemas, generated data, and automated tests without requiring live external services.
- [ ] Publication provides a stable latest JSON endpoint and immutable versioned snapshots.
- [ ] TKKGTracker can consume the published data without retaining a competing scraper or catalogue.
- [ ] TKKGDownloader can consume the published data without independent episode or release discovery.
- [ ] Documentation explains ownership, schema versioning, provenance, source coverage, publication, and consumer migration.
- [ ] A migration audit records source files moved, retained, replaced, or retired in each repository.
- [ ] Existing applications continue to work during staged migration, with no premature removal of their current data path.

## Dependencies
- TKKGtracker request 009 and its current branch/PR work must be audited before moving or closing anything.
- TKKGtracker's current main-branch scraper, schema, generated catalogue, and knowledge base are the baseline for migration.
- TKKGDownloader's current episode and Spotify resolution pipeline is the baseline for consumer changes.
- TKKGData must publish a validated initial dataset and stable contract before either consumer switches its production data source.

## Open questions
- Should the public latest dataset be served directly from the TKKGData main branch, GitHub Pages, or both, and what cache headers are practical?
- What is the exact versioning policy for schema changes and immutable dataset releases?
- Should raw source snapshots be retained in the repository, as fixtures, or as downloadable build artifacts?
- Which additional TKKG content categories should be included after the regular main series is migrated?
- What review mechanism should be used for candidate mappings that cannot be verified automatically?
