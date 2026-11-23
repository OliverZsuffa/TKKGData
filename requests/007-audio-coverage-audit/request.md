# Request 007: Separate missing audio episodes from discovery problems

## Goal
Provide an operational queue separating episodes that simply have not yet been successfully discovered from episodes where discovery previously encountered an issue. The user should be able to run the first group through discovery and investigate the second.

## Desired output
Two clear lists:
1. **Ready for discovery:** missing verified mapping and no recorded issue from discovery.
2. **Needs investigation:** missing verified mapping but a recorded discovery attempt produced a failure, rejected/unusable candidates, or incomplete resolution.

Each investigation entry should include episode number, title, last failure category and reason, stage, timestamp and useful diagnostic details, when available. Both lists should include copy-ready selections for the existing workflow.

## Scope
- Audit the entire catalogue and classify missing episodes into the two operational groups.
- Establish a durable issue history, so episodes discovered to have problems remain flagged across runs. Track episode number, attempt time, stage, failure category, reason, and concise diagnostics.
- Update issue history when discovery runs: newly unresolved outcomes enter or update the issue record; a successful verified mapping clears the outstanding issue. Avoid overwriting verified mappings.
- Provide copy-ready episode selection, grouped into manageable batches, for the existing Audio enrichment workflow.
- Publish GitHub Actions job summary and downloadable JSON/Markdown report.
- Keep the audit itself read-only and manually triggered. It must not run discovery or modify the episode catalogue.

## Acceptance criteria
- Every missing mapping appears in exactly one operational list.
- Episodes without known issues are immediately selectable for discovery.
- Known problematic cases include useful last-attempt diagnostics.
- An episode moves to the investigation list when a discovery attempt fails, and leaves the outstanding issue list after successful verification.
- Existing catalogue verification and publication safeguards remain intact.
- Automated tests cover classification, persistence/update logic, selection formatting and ordering.
