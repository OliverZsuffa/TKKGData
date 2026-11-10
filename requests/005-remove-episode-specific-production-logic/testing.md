# Testing plan

## Automated tests
1. Run `python -m unittest discover -s tests -v`.
   Expected: all existing tests and new generic diagnostic tests pass.
2. Run `python -m py_compile scraper/audio_enrichment.py scraper/audio_source_experiments.py`.
   Expected: no syntax errors.
3. Validate the catalogue using the repository's validation command.
   Expected: all episode records and existing verified mappings remain valid.
4. Parse the workflow YAML.
   Expected: valid workflow syntax, scheduled and manual triggers present, no push-only special path.
5. Search production Python and workflow files for the former fixed episode number, title, and playlist ID.
   Expected: no matches. Test files may retain episode-specific fixtures.

## Diagnostic script tests
- A requested episode is loaded by number from the canonical catalogue.
- An unknown episode is rejected with a clear error.
- Search queries contain the selected episode number and title, not a fixed title.
- No playlist ID is assumed when none is supplied.
- An explicitly supplied playlist ID is passed only for the selected episode.

## Workflow behaviour
- Manual dispatch with no episode processes missing mappings within the configured limit.
- Manual dispatch with an episode selects that episode.
- A supplied playlist ID is accepted only with one selected episode.
- Manual writes remain opt-in.
- Scheduled runs select latest missing mappings and write verified results.
