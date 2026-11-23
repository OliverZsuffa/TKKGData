# Implementation plan

## Design
1. Add a durable issue ledger (proposed `data/audio-discovery-issues.json`) separate from the canonical episode catalogue. Store only unresolved issues, keyed by episode number, with episode title, last attempted timestamp, failure stage/category, human-readable reason, and concise relevant diagnostic context. Keep structure versioned.
2. Hook the existing discovery aggregation/publishing workflow into ledger maintenance. Failed or unresolved results update the ledger; verified success clears that episode's outstanding issue. Ensure these changes are committed reliably, including dry-run dispatches where appropriate, without accidentally publishing unverified catalogue mappings. Review permissions and commit behavior explicitly.
3. Build an audit module reading the canonical catalogue and ledger. For each unverified episode: if ledger contains an issue, classify **Needs investigation**; otherwise **Ready for discovery**. If ledger is missing or corrupt, report an explicit warning and do not silently claim issue-free history.
4. Add a manually triggered read-only GitHub Actions audit. It publishes both groups, full diagnostics, copy-ready CLI selection and workflow-dispatch selections, grouped in batches, as Markdown summary and JSON artifact.
5. Copy-ready selections should be concise and practical. Provide repeated `--episode` command selections and numbered episode lists for dispatching the existing workflow in groups of at most 10.
6. Historical attempts before the ledger exists cannot be reliably reconstructed from ephemeral reports. First-run episodes should be in the Ready for discovery group unless a durable source provides evidence of a past issue. Document this migration limitation.
7. Tests: ledger update/clear, classification, data validation, selection formatting, ordering, corrupt/missing ledger handling, full coverage and empty cases.
8. Update README/request index, run complete offline tests, compilation, catalogue contract validation and workflow syntax checks.

## Expected files
- `data/audio-discovery-issues.json`
- audit module and tests
- update existing aggregation workflow/module for issue-ledger maintenance
- `.github/workflows/audio-coverage-audit.yml`
- docs and request documentation
