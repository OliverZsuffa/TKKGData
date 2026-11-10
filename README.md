# TKKGData

The canonical, validated dataset for TKKG episodes and their releases. TKKGData is the only repository responsible for discovering, scraping, reconciling, validating, and publishing shared TKKG metadata.

Consumers:
- [TKKGTracker](https://github.com/OliverZsuffa/TKKGtracker) provides the listening tracker and stores personal progress locally.
- [TKKGDownloader](https://github.com/OliverZsuffa/TKKGDownloader) downloads and merges audio locally.

## Current data

The published compatibility endpoint is:

    https://raw.githubusercontent.com/OliverZsuffa/TKKGData/main/data/episodes.json

Dataset metadata and schema version are published separately at:

    https://raw.githubusercontent.com/OliverZsuffa/TKKGData/main/data/dataset-metadata.json

The episode JSON remains an array so consumers can adopt it without changing their application behaviour. New optional fields, including verified audio release mappings, are additive. Consumers must tolerate missing enrichment.

The catalogue contains 243 episode records. Audio enrichment is an independent, optional layer. Current published coverage is one verified audio release mapping, with 40 Spotify and YouTube Music track pairs. The weekly workflow attempts up to five of the highest-numbered episodes without verified audio mappings.

## Ownership

TKKGData owns episode and release metadata, source provenance, source adapters, scraping, normalization, reconciliation, Spotify album metadata, provider track records, verified YouTube Music playlist and individual song URLs, validation, and publication.

TKKGTracker owns its user interface, local listening progress, ratings, notes, favourites, and preferences. TKKGDownloader owns local download execution, FFmpeg merging, output files, and download preferences. Neither consumer may scrape source websites or write metadata back to TKKGData.

## Development

Requirements: Python 3.11 or later.

Install core dependencies:

    py -m pip install -r requirements.txt

Install audio metadata discovery dependencies:

    py -m pip install -r requirements-audio.txt

Run the catalogue scraper:

    py -m scraper.run

Resolve one episode into provider links without writing to the catalogue:

    py -m scraper.audio_enrichment --episode EPISODE_NUMBER

Prepare a range for parallel discovery. The workflow dispatch accepts inclusive start and end episode numbers, with five episodes per batch and four concurrent batches by default:

    py -m scraper.audio_enrichment_batch prepare --start-episode 1 --end-episode 243 --batch-size 5 --max-parallel 4

To run it, open GitHub Actions, select **Audio enrichment**, and choose **Run workflow**. Set the start and end episode numbers, batch size, and parallelism. Start with write mode disabled, inspect the combined report, then repeat with write mode enabled when the results are acceptable. For the full catalogue, use start 1 and end 243. Discovery batches are always dry-run only. A single aggregation job validates every report and is the only job allowed to publish the catalogue. The scheduled run remains latest-first and limited to five missing mappings.

The JSON report contains the Spotify album URL, ordered Spotify track URLs, the verified YouTube Music playlist or album page URL, and ordered YouTube Music song URLs. If YouTube Music matching remains unresolved, the report still retains the successfully resolved Spotify links and stage-specific failure diagnostics.

Write only fully verified mappings:

    py -m scraper.audio_enrichment --episode EPISODE_NUMBER --write

An optional playlist ID can be supplied for one selected episode when diagnosing or recovering a known playlist:

    py -m scraper.audio_enrichment --episode EPISODE_NUMBER --playlist-id PLAYLIST_ID

Run all offline tests:

    py -m unittest discover -s tests -v

Live episode-number-to-links integration tests cover a small regression matrix and run separately from offline tests. Network discovery is not required for catalogue validation. Respect source terms, robots.txt, rate limits, and access restrictions.

## Publication and versioning

The stable latest compatibility dataset is data/episodes.json. data/dataset-metadata.json describes the schema version, dataset generation time, episode count, and covered series. Git commit SHAs provide immutable snapshots. GitHub Actions validates the dataset before committing generated changes. A failed scrape or validation must not replace the last known valid dataset.

## Development workflow

Read the project instructions, documentation index, and knowledge base before changing the project. Substantial work requires a numbered request and an approved implementation plan. See requests/README.md.

The three repository migration is tracked by Request 001. TKKGTracker and TKKGDownloader now consume the published TKKGData contract. The tracker application retains its existing behaviour, progress storage, and offline capability.
