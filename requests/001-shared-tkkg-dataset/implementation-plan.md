# Implementation plan: Establish TKKGData as the shared TKKG dataset

**Status:** Approved by Oliver on 2026-11-09. Implementation in progress.

## 1. Architecture and ownership

Target architecture:

    Official TKKG sources and permitted public provider metadata
                              |
                              v
                           TKKGData
       discovery, scraping, reconciliation, schema, provenance,
                 validation, reports, and publication
                              |
                     versioned JSON dataset
                         /          \
                        v            v
                  TKKGTracker  TKKGDownloader
                  UI and local  download execution
                  user progress and local files

Ownership rules:
- TKKGData owns every shared episode fact, release mapping, provider identifier, source URL, provenance record, and validation rule.
- TKKGTracker owns UI state and user-specific listening progress only.
- TKKGDownloader owns download execution and local output state only.
- Neither consumer may scrape source websites, invent missing metadata, or maintain a second authoritative catalogue.
- A consumer may cache a published snapshot for resilience. A cache is not an independently editable source of truth.

## 2. Repository foundation

Establish and maintain:
- README with purpose, quick start, data scope, source policy, and publication link.
- .github/copilot-instructions.md with request approval workflow and data integrity rules.
- requests/README.md, requests/TEMPLATE.md, and numbered request folders.
- docs/README.md, docs/decisions.md, and docs/knowledge/.
- .gitignore, Python project/dependency configuration, and GitHub Actions checks.
- A reproducible local validation command that does not require network access.

Do not select a complex framework or runtime before inspecting the existing scraper and choosing the smallest maintainable migration path.

## 3. Baseline inventory and migration audit

Before moving code:
1. Record the current main branch commit and working state of all three repositories.
2. Inventory TKKGtracker's scraper modules, schemas, generated JSON/CSV, fixtures, workflows, documentation, and request 009 branch/PR.
3. Inventory TKKGDownloader's metadata fetching, Spotify lookup, track validation, download selection, merging, tests, and documentation.
4. Identify every consumer of TKKGtracker's current JSON and CSV endpoints.
5. Compare the latest generated catalogue with the current published catalogue. Record row counts, episode-number coverage, schema validation, and known source gaps.
6. Preserve verified source findings and fixtures. Do not copy a stale generated file over newer data.
7. Produce a file-by-file migration table: move to TKKGData, replace with consumer, retain as app-specific, or retire after cutover.

The migration audit is a deliverable and must be reviewed before deleting or disabling existing functionality.

## 4. Canonical dataset model

The initial consumer compatibility contract deliberately preserves the existing flat TKKGTracker episode array and its field names. This avoids changing tracker runtime behaviour. Dataset metadata and schema version are published in a sidecar file. New enrichment fields are additive. The long-term model still needs explicit release and provider relationships, but those additions must retain the compatibility view consumed by existing apps.

Proposed logical entities:
- Dataset metadata: schema version, dataset version, generated timestamp, source coverage summary.
- Series or collection: regular main series initially, with explicit support for future categories without silently mixing them.
- Episode: stable ID, series ID, episode number where applicable, canonical title, aliases, synopsis, artwork references, and episode-level facts.
- Release: one or more physical or digital editions associated with an episode, with release date/text, label, EAN, and edition metadata where sourced.
- Provider release: Spotify album, YouTube Music playlist, or another provider album/release, with provider ID, canonical URL, title, artist identity, track count, source provenance, and verification status.
- Provider track: track number, title, artist, duration and provider ID/URL where available. Keep Spotify and YouTube Music track records distinct and link matched tracks explicitly.
- Archive chapter: chapter number/title and archive timing or segmentation metadata. This is not interchangeable with a provider track.
- Source record: source name, URL, retrieval timestamp, field coverage, and extraction method.
- Relationship: explicit links between episodes, releases, editions, collections, and alternative versions.

Modelling constraints:
- One episode may have several releases and provider releases.
- One provider release may contain a variable number of tracks. Derive counts from validated returned track records, not a potentially inconsistent summary field.
- YouTube Music must store both the playlist mapping and individual song mappings when independently verified.
- A missing provider is normal and must be representable.
- Use null or omission consistently for unavailable values. Never use fabricated placeholder IDs.
- Keep source-specific raw evidence available for audit without exposing unverified candidates as verified consumer data.
- Define stable IDs and canonical URL rules before migrating records.

Initial implementation uses schema version 1.0.0 and preserves the legacy episode-array shape. The episode schema includes optional verified audio release data. Further multi-edition modelling must be introduced additively or through a versioned compatibility projection, never by silently breaking the tracker contract.

## 5. Source adapters and scraping

Move source acquisition from TKKGtracker into independent TKKGData adapters.

Initial migration candidates:
- Official TKKG product catalogue and detail pages.
- Historical TKKG archive pages and their metadata.
- Official episode-specific Linkfire listening hubs.
- Spotify metadata resolution already explored in TKKGDownloader and the audio enrichment branch.
- YouTube Music playlist discovery and playlist retrieval.
- YouTube Music individual song search and matching.

For each adapter:
1. Define the fields it can establish and the evidence required.
2. Store source URL and retrieval time.
3. Use saved fixtures for deterministic tests.
4. Respect robots.txt, terms, rate limits, caching, and access restrictions.
5. Handle source outages and partial records independently.
6. Never let a failed optional source erase valid data from another source.
7. Keep candidate discovery separate from publication.

Do not assume an unofficial client is stable or authorized merely because it works. Recheck feasibility and source restrictions during implementation.

## 6. Reconciliation, enrichment, and verification

Use a pipeline with explicit stages:
1. Discover candidate records from each source.
2. Normalize identifiers, text, dates, and URLs without discarding meaningful distinctions.
3. Match source records to stable episode identities.
4. Reconcile field values using documented source precedence and retain conflicting evidence.
5. Discover provider releases and track lists.
6. Match Spotify and YouTube Music releases using episode identity, artist identity, ordered titles, durations, and track counts.
7. Mark a provider mapping verified only when all required checks pass.
8. Preserve existing verified mappings when a new run is incomplete, ambiguous, or unavailable.
9. Emit a machine-readable report for new, updated, unchanged, unresolved, rejected, and conflicting records.
10. Publish only after the entire generated dataset passes validation and completeness guards.

Episode 150 must be a regression case. Validate actual Spotify track records and actual playlist/song records. Do not hardcode the count or infer completeness from a provider summary count alone.

Provide a curated correction or override mechanism for cases that cannot be resolved automatically. Overrides must include a reason and evidence, and must be validated like scraped data.

## 7. Dataset build, validation, and publication

Proposed repository outputs:
- Canonical generated JSON dataset.
- Optional CSV export for inspection and analysis, generated from JSON.
- JSON Schema and schema version.
- Source coverage and scrape report.
- Saved fixtures and automated tests.

Validation should include:
- JSON Schema validation.
- Unique stable IDs and valid relationships.
- Episode numbering and series-specific completeness checks.
- URL host and provider ID consistency.
- Track ordering, uniqueness, and count consistency.
- Provenance and verification metadata requirements.
- Preservation checks preventing unexplained removal or downgrade of verified records.
- A diff/report showing additions, updates, removals, and conflicts.

Publication proposal:
- Stable latest dataset URL under the TKKGData repository.
- Immutable snapshots associated with tagged dataset releases.
- Dataset metadata containing schema version, dataset version, and generated timestamp.
- CI validates before publication. Failed validation must leave the last published valid dataset untouched.
- Consumers pin a compatible schema range and may use latest data while retaining a last-known-good local cache.

The final endpoint and tag strategy remain an approval-stage design choice.

## 8. Consumer migration

### TKKGTracker
- Replace its in-repository scraper and generated catalogue dependency with the TKKGData published JSON endpoint.
- Remove scraping and schema ownership only after the new data source is proven in production.
- Keep local listening progress, ratings, notes, favourites, and settings in browser storage.
- Preserve offline behaviour by caching the last valid dataset snapshot.
- Validate dataset version and structure before replacing the cached copy.
- Keep UI rendering resilient when optional metadata is absent.
- Remove the old weekly scraper workflow and catalogue generation only after cutover verification.
- Update its README, knowledge base, and deployment workflow to describe the consumer role.

### TKKGDownloader
- Replace the TKKGTracker catalogue URL with the TKKGData published dataset endpoint.
- Resolve episode identity and official title from TKKGData.
- Consume verified Spotify album metadata and YouTube Music playlist and individual track URLs.
- Prefer exact verified source mappings over free-text rediscovery.
- Keep track count and order validation based on actual returned records.
- Verify the installed downloader tool's supported pairing/direct-source behaviour before selecting the exact download invocation.
- Retain a clearly reported fallback only for episodes without verified audio mappings. The fallback must not write discoveries back to the dataset.
- Keep FFmpeg merging, output naming, overwrite protection, and local file handling in TKKGDownloader.
- Update its README, knowledge base, and tests.

The two consumer changes are separate requests in their own repositories and depend on the TKKGData contract and publication being available.

## 9. Coordinated rollout

1. Approve the three repository plans and the shared architecture.
2. Complete TKKGData repository foundation and baseline audit.
3. Implement the schema, migration, and data pipeline in TKKGData.
4. Validate the migrated catalogue against the current TKKGtracker output.
5. Complete episode 150 audio mapping as a fully tested regression case.
6. Publish the first versioned dataset and document the consumer contract.
7. Migrate TKKGTracker to consume TKKGData. Verify online, offline, refresh, and progress preservation.
8. Migrate TKKGDownloader to consume TKKGData. Verify metadata resolution, exact track selection, download, merge, and output protection on Windows.
9. Run cross-repository compatibility checks and compare results with the old workflows.
10. Only after successful cutover, retire the old scraper, data files, and workflows from TKKGtracker and remove duplicate metadata resolution from TKKGDownloader.
11. Update all three knowledge bases and request notes with actual results.

Never remove the old data path before its replacement is live and verified.

## 10. Testing and release gates

- Unit tests for normalization, parsing, matching, reconciliation, schema validation, and publication.
- Fixture tests for each source adapter and known inconsistencies.
- Regression tests for episode 150, variable track counts, missing sources, ambiguous candidates, and preservation of verified data.
- Offline tests that do not contact external services.
- Live source diagnostics run separately and bounded.
- Consumer contract tests against a published fixture and a real versioned snapshot.
- Tracker manual tests for catalogue load, refresh, offline launch, progress preservation, and optional fields.
- Downloader manual tests on Windows for single episodes, ranges, exact source selection, merging, overwrite protection, and playback.
- CI must pass in all three repositories before the old architecture is retired.

## 11. Risks and mitigations

- Source markup and unofficial provider interfaces change: isolate adapters, use fixtures, report coverage, and fail safely.
- Existing catalogue fields may have implicit consumers: inventory every consumer and preserve compatibility during migration.
- Duplicate or conflicting releases: model multiple releases and require evidence-based verification.
- Provider track count metadata may be inconsistent: derive counts from actual validated records.
- Consumer network failure: retain last-known-good data in the tracker and provide clear downloader errors.
- Breaking schema changes: version the schema and publish immutable snapshots.
- Migration accidentally loses curated data: compare old and new datasets and require a reviewable migration report before cutover.

## 12. Definition of done

The architecture is complete only when TKKGData is the sole maintained source of shared episode data, both applications consume its published contract, no consumer performs duplicate source scraping, user progress remains private to TKKGTracker, download execution remains in TKKGDownloader, all automated checks pass, and the old data paths have been retired only after verified cutover.
