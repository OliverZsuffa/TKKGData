# Dataset architecture principles

**Status: implemented baseline contract.** The compatibility dataset and two consumer integrations are live.

## Ownership
- TKKGData owns shared episode metadata, source discovery, scraping, normalization, validation, provenance, audio enrichment, and publication.
- TKKGTracker consumes the published dataset at build time. It owns the app, personal listening progress, ratings, notes, favourites, and preferences.
- TKKGDownloader consumes the published dataset read-only. It owns local downloads, download preferences, track-file validation, and FFmpeg merging.

## Current compatibility contract
- The stable episode dataset is data/episodes.json.
- It remains a JSON array with the original TKKGTracker episode record shape and field names.
- The stable dataset metadata sidecar is data/dataset-metadata.json.
- The current schema version is 1.0.0.
- New fields such as audio_release are optional and additive.
- Git commit SHAs provide immutable snapshots. The main branch URLs provide the latest snapshot.
- Consumers must validate the metadata version and episode count before use.

The initial migration transferred 243 episode records byte-for-byte from TKKGTracker main. TKKGTracker's deployment fetches the latest dataset, validates it, and includes it at its existing same-origin runtime path. This preserves the existing app, service worker, and offline behaviour.

## Modelling principles
- The current episode number is the stable lookup key for the regular numbered series.
- Model archive chapters separately from provider release tracks. Their divisions are not interchangeable.
- Store source URL, retrieval time, source identity, and verification status for sourced fields.
- Distinguish candidate discoveries from verified published mappings.
- Preserve unresolved conflicts for review rather than silently selecting one candidate.
- Keep personal progress and preferences outside the shared dataset.
- The current audio model supports one optional verified audio_release object per episode. Multiple editions and release variants require a future additive model and compatibility projection.

## Publication principles
The latest episode array and metadata sidecar are published on main. GitHub Actions validates the catalogue before committing generated changes. A failed scrape or validation must not replace the last known valid dataset. The catalogue refresh and audio enrichment workflows share a concurrency group and rebase generated commits on the latest main before pushing.
