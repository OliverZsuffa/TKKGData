# Approved decisions

## 001. Preserve the tracker catalogue compatibility shape

Oliver approved the three-repository migration on 2026-11-09, with an explicit requirement that TKKGTracker must not lose or change any existing application functionality.

The first TKKGData publication therefore retains the current TKKGTracker data/episodes.json array and existing episode fields. Dataset metadata and schema version are published in a separate sidecar file. New fields, including verified audio metadata, are additive. TKKGTracker should receive the new catalogue at build time so its existing same-origin service-worker caching and offline behaviour remain intact.

## 002. Separate shared data from personal application state

TKKGData owns shared episode facts, releases, provider mappings, source provenance, scraping, validation, and publication. TKKGTracker retains all user progress and preferences locally. TKKGDownloader retains local downloads and merge behaviour. Consumers are read-only and do not independently scrape or publish shared metadata.
