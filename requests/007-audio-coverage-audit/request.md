# Request 007: Audio coverage audit and copy-ready discovery selection

## Goal
Add a manually triggered GitHub Actions audit that identifies every catalogue episode without a verified audio listening mapping, and presents the selection in copy-ready formats for the existing audio discovery workflow. Make unresolved discovery outcomes easier to distinguish and investigate, including cases where discovery returns irrelevant or unusable results.

## Scope
- Read the current canonical episode catalogue and identify all episodes lacking a verified audio_release mapping.
- Generate an audit report with episode number and title, missing or partial mapping details, and a copy-ready selection for the discovery CLI and workflow inputs.
- Include an explicit classification of missing data, such as never enriched, Spotify unresolved, YouTube Music unresolved, incomplete track mapping, or discovery failure, where evidence exists. Avoid asserting a failure category without evidence.
- Where prior discovery reports or persisted diagnostic data are available, surface those outcomes and their failure stage/reason. Identify limitations if historic failed runs are not persisted.
- Output a concise GitHub Actions job summary and a downloadable artifact with full report and copy-ready snippets.
- Keep this audit read-only. It must not modify the canonical catalogue or trigger enrichment automatically.

## Acceptance criteria
- Covers the full catalogue and correctly counts verified versus missing mappings.
- Missing episodes are ordered and presented clearly, including episode numbers and titles.
- Copy-ready CLI commands include repeated --episode arguments and avoid exceeding command-line practical limits by offering batch/range alternatives.
- The output explains that the existing workflow supports individual episodes or inclusive ranges and helps users prepare dispatch selections.
- Results distinguish confirmed evidence from inferred or unknown causes.
- Automated tests cover the report and selection output.
