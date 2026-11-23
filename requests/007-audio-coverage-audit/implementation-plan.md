# Implementation plan

## Proposed design
1. Add a focused audit module (for example scraper/audio_coverage_audit.py) that loads the canonical catalogue, reuses the existing verification-status definition, and computes coverage and per-episode missing status.
2. Derive classifications from actual data fields only. At minimum, distinguish no audio_release record, non-verified status, absent Spotify information, absent YouTube Music playlist/track mappings, and track-count or pairing incompleteness when detectable. Do not fabricate discovery history.
3. Add a GitHub Actions workflow manually triggered, read-only, with no contents write permission. The workflow installs only necessary project dependencies, runs the audit, uploads the report artifact, and publishes a summary.
4. Report formats: human-readable Markdown summary, JSON audit report, and copy-ready command snippets. CLI selection should use repeated --episode flags. Provide a selection string or CSV-like episode number list usable when dispatching the existing workflow, and group output into batches of at most 10 for manageability.
5. Investigate whether failed discover run artifacts can be reliably accessed from the audit workflow. If not, clearly scope failure-history analysis to persisted sources and add a separate design recommendation for retaining failure summaries, rather than making this workflow depend on ephemeral Actions artifacts.
6. Add tests for classification, full coverage counts, ordering, snippets, and empty or malformed records.
7. Update documentation, request index, and request notes with results.

## Files expected
- scraper/audio_coverage_audit.py (or equivalent)
- .github/workflows/audio-coverage-audit.yml
- tests
- docs/README.md or project README as appropriate
- request folder documents
