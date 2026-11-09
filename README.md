# TKKGData

The canonical, validated dataset for TKKG episodes and their releases. TKKGData is the only repository responsible for discovering, scraping, reconciling, validating, and publishing shared TKKG metadata.

Consumers:
- [TKKGTracker](https://github.com/OliverZsuffa/TKKGtracker) provides the listening tracker and stores personal progress locally.
- [TKKGDownloader](https://github.com/OliverZsuffa/TKKGDownloader) downloads and merges audio locally.

## Current data

The initial migration preserves the existing tracker catalogue without changing its episode record structure. The published compatibility endpoint is:

    https://raw.githubusercontent.com/OliverZsuffa/TKKGData/main/data/episodes.json

Dataset metadata and schema version are published separately at:

    https://raw.githubusercontent.com/OliverZsuffa/TKKGData/main/data/dataset-metadata.json

The episode JSON remains an array so the current TKKGTracker can adopt it without changing its application behaviour. New optional fields, including verified audio release mappings, are additive. Consumers must tolerate unknown optional fields and missing enrichment.

The initial migration contains 243 episode records, numbered 1 through 243, copied from the TKKGTracker main branch snapshot. Existing source provenance, episode details, and official listening links are retained.

Audio enrichment is an independent, optional layer. As of 2026-11-09, episode 150 is the first verified release mapping, with its 40 Spotify and YouTube Music tracks paired individually. The other 242 episodes remain in the enrichment queue. The weekly workflow attempts up to five of the highest-numbered episodes without verified audio mappings.

## Ownership

TKKGData owns episode and release metadata, source provenance, source adapters, scraping, normalization, reconciliation, Spotify album metadata, provider track records, verified YouTube Music playlist and individual song URLs, validation, and publication.

TKKGTracker owns its user interface, local listening progress, ratings, notes, favourites, and preferences. TKKGDownloader owns local download execution, FFmpeg merging, output files, and download preferences. Neither consumer may scrape source websites or write metadata back to TKKGData.

## Development

Requirements: Python 3.11 or later.

Install core dependencies:

    py -m pip install -r requirements.txt

Install optional audio discovery dependencies:

    py -m pip install -r requirements-audio.txt

Run the catalogue scraper:

    py -m scraper.run

Discover verified audio mappings without writing them:

    py -m scraper.audio_enrichment --episode 150

Write only fully verified audio mappings:

    py -m scraper.audio_enrichment --episode 150 --write

Run diagnostics for audio source matching:

    py -m scraper.audio_source_experiments --episode 150

Run all offline tests:

    py -m unittest discover -s tests -v

Network discovery is not part of the offline test suite. It runs only through explicit scraper or enrichment commands and scheduled workflows. Respect source terms, robots.txt, rate limits, and access restrictions.

## Publication and versioning

The stable latest compatibility dataset is data/episodes.json. data/dataset-metadata.json describes the schema version, dataset generation time, episode count, and covered series. Git commit SHAs provide immutable snapshots. GitHub Actions validates the dataset before committing generated changes. A failed scrape or validation must not replace the last known valid dataset.

## Development workflow

Read the project instructions, documentation index, and knowledge base before changing the project. Substantial work requires a numbered request and an approved implementation plan. See requests/README.md.

The three repository migration is tracked by Request 001. TKKGTracker and TKKGDownloader now consume the published TKKGData contract. The tracker application retains its existing behaviour, progress storage, and offline capability.
