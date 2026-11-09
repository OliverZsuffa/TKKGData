# Notes: Request 003

## Findings
- The first audio enrichment workflow run failed because spotDL requires FFmpeg even for metadata resolution.
- The first catalogue refresh completed scraping and validation, but its generated commit was rejected because another workflow updated main while it was running.
- Both issues are operational workflow configuration problems, not failures in the scraper's validation logic.

## Implementation
- Added FFmpeg installation to the audio workflow.
- Unified the data-writing workflows under one concurrency group.
- Added pull --rebase origin main before generated data pushes.
- Added the catalogue workflow file to its own push path filter.

## Test results
Pending workflow execution after merge.
