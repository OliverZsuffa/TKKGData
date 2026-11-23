# Testing plan

- Unit tests for missing verified mapping classification into Ready for discovery versus Needs investigation.
- Ledger tests for new failures, repeat failures updating details, verified successes clearing issues, and unrelated records being retained.
- Verify that failure stages, categories, reasons and diagnostics are preserved without overstating evidence.
- Test copy-ready commands and selections, chunking and ordering.
- Test missing/corrupt ledger behavior with explicit warning.
- Test fully verified and empty catalogues.
- Run complete offline test suite, Python compilation and catalogue contract validation.
- Manually dispatch the read-only audit workflow and confirm both lists, summary and report artifact. Verify issue-ledger changes are handled by discovery aggregation, not by the audit.
