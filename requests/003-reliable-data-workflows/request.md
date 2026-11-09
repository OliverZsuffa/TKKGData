# Request 003: Make live data workflows reliable

## Status
Approved as operational work under Request 001 on 2026-11-09.

## Objective
Ensure the scheduled catalogue and audio enrichment workflows can execute and publish validated data safely.

## Requirements
1. Install FFmpeg before running spotDL metadata operations in CI.
2. Serialize workflows that write to the same dataset files.
3. Rebase generated data commits on the latest main before pushing.
4. Ensure scraper workflow changes trigger a validation and refresh run.
5. Preserve the last-known-good dataset if scraping, validation, or publication fails.
6. Upload reports even when a workflow fails.

## Acceptance criteria
- [ ] Audio enrichment workflow has FFmpeg available.
- [ ] Catalogue and audio write workflows share one concurrency group.
- [ ] Both generated data commits pull/rebase main before pushing.
- [ ] Updating the catalogue workflow itself triggers the workflow.
- [ ] CI validates workflow code and dataset contract.
