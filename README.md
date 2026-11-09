# TKKGData

The shared, validated source of truth for structured TKKG episode and release data.

TKKGData is the central data project for [TKKGTracker](https://github.com/OliverZsuffa/TKKGtracker), [TKKGDownloader](https://github.com/OliverZsuffa/TKKGDownloader), and future TKKG tools.

## Responsibilities

TKKGData is intended to own:
- Episode discovery and source scraping.
- Metadata normalization and reconciliation.
- Episode, release, and provider data schemas.
- Spotify and YouTube Music release discovery and verification.
- Source provenance, validation, and coverage reporting.
- Publication of a stable, versioned JSON dataset.

Applications consume the published dataset. They do not maintain independent episode catalogues or duplicate source scraping.

## Repository status

The repository foundation and proposed architecture are documented in [Request 001](requests/001-shared-tkkg-dataset/request.md). The migration is currently in planning and requires explicit approval before implementation.

## Development

Read the [project instructions](.github/copilot-instructions.md), [documentation index](docs/README.md), and [knowledge base](docs/knowledge/README.md) before contributing.

Substantial work follows the request workflow in [requests/README.md]. Each request includes acceptance criteria, an implementation plan, a testing plan, and implementation notes.

## Data integrity

Only evidence-backed, validated records should be published. Candidate discoveries and unresolved conflicts must remain distinguishable from verified data. Source failures must not erase previously verified records. Respect source terms, robots.txt, and access restrictions.

User-specific listening progress belongs in TKKGTracker. Download preferences and local files belong in TKKGDownloader.
