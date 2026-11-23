# Testing plan

- Unit tests against fixture catalogues for verified coverage, missing audio_release, partial data, non-verified status, and invalid record shapes.
- Validate that episode numbers and titles are sorted consistently and classification does not overstate certainty.
- Verify copy-ready commands include the correct repeated --episode values and chunk selections.
- Test a fully verified catalogue and an empty catalogue.
- Run the complete offline test suite, Python compilation, and catalogue contract validation.
- Manual GitHub Actions dispatch: verify job summary and artifact contain the full audit, and confirm the workflow has read-only permissions and makes no catalogue writes.
