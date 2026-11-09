# Dataset architecture principles

**Status: proposal in request 001. Not an approved implementation contract.**

## Intended ownership
TKKGData is intended to own source discovery, scraping, normalization, validation, provenance, and publication of the shared TKKG dataset.

TKKGTracker is intended to consume episode data and own only application-specific listening progress and presentation.

TKKGDownloader is intended to consume episode and release data and own only download execution, local files, and download preferences.

## Modelling principles
- Give each episode a stable identifier independent of display title.
- Model an episode separately from its physical and digital releases.
- Model provider albums/playlists separately from provider tracks.
- Preserve the difference between archive chapters and streaming release tracks.
- Allow multiple editions or provider releases for one episode.
- Record source URL, retrieval time, source identity, and verification status for sourced fields.
- Distinguish discovered candidates from verified published mappings.
- Preserve unresolved conflicts for review rather than silently selecting one candidate.
- Keep personal progress and preferences outside the shared dataset.

## Publication principles
The intended consumer contract is a versioned JSON dataset with a documented schema. A stable latest snapshot and immutable tagged snapshots should both be available. Consumers should validate the dataset version and retain a last-known-good cached copy where appropriate.

The concrete schema, endpoint, versioning policy, and publication mechanism remain open until request 001 is approved and implemented.
