# Implementation plan

## 1. Establish the Spotify metadata evidence model
- Inspect the pinned spotDL 4.5.2 API and use its raw song-search result interface rather than `Song.from_search_term()` as the sole candidate source.
- Preserve a bounded set of candidate records containing Spotify track ID and URL, track title, artist names and IDs where exposed, album ID and title, track number, duration, and query provenance.
- Generate a small set of query variants from the canonical episode number and title. Include split-track and whole-episode naming forms without introducing individual episode branches.
- Deduplicate candidates by stable Spotify track ID.
- Add deterministic normalization for Unicode, punctuation, whitespace, leading episode numbers, and common part-number notation. Keep the original provider strings for diagnostics.
- Do not make network calls for every possible spelling. Use bounded queries and candidate counts, cache repeated metadata within a run where the library supports it, and apply bounded retry/backoff only to transient provider failures.

## 2. Validate artist identity and score Spotify candidates
- Establish the exact artist names and Spotify artist IDs actually returned for historical releases before finalizing the accepted alias table.
- Treat `TKKG` and any confirmed historical credit such as `TKKG Retro-Archiv` as explicit aliases. Prefer stable artist IDs when reliably available, with exact normalized names as a compatibility check.
- Reject artists that merely contain TKKG as a substring unless the identity has been explicitly verified and added as an alias.
- Score candidates using independent evidence: exact episode number, exact normalized episode title, expected split-track part marker, artist identity, album title, and corroborating album or release metadata.
- Require strong episode identity and a unique best candidate. A generic TKKG artist credit alone is not sufficient.
- Record candidate score components and rejection reasons. Keep the threshold and tie policy explicit and covered by tests.

## 3. Classify the Spotify release format
- Retrieve the parent album metadata for promising candidates.
- Classify the result generically as either:
  1. A dedicated split-track episode release, where the album's ordered tracks consistently identify the same episode and form a complete part sequence.
  2. A single-track episode recording contained within a larger compilation, where the selected track itself identifies the requested episode but the parent album also contains unrelated episodes.
- For a dedicated episode album, retain the full ordered album tracklist after checking every track belongs to the requested episode.
- For a compilation, select only the exact episode track or contiguous episode-specific tracks. Do not include tracks belonging to neighbouring episodes. Retain the parent album ID and URL as provenance, while the selected individual track URLs remain the precise episode entry points.
- If a compilation contains several plausible tracks for the same episode, or the episode boundaries cannot be established, reject it as ambiguous.
- Validate stable track IDs, album identity, track numbers, titles, and available durations. Do not assume a fixed track count such as 40.
- Review the current JSON schema and downstream consumers. Prefer the existing album plus selected track representation if it is unambiguous. If it is not, propose a minimal additive field that distinguishes a compilation source from a dedicated episode album before implementation.

## 4. Build historical Spotify regression coverage
- Add fixture-based tests for artist aliases, unrelated artists, multiple search results, duplicate candidates, ranking, ties, missing metadata, and transient provider errors.
- Add release-format fixtures for a dedicated split-track album and a compilation containing several different episodes.
- Assert that only the requested episode's track or tracks are selected from a compilation.
- Add explicit regression fixtures for episodes 1, 2, 20, 37, 53, and 100. Fixtures must capture observed metadata and must not invent IDs or track counts.
- Keep the existing episode 100+ release behaviour intact.
- Add a live dry-run regression matrix for representative old episodes after fixture tests pass. Reports must distinguish end-to-end successes from unresolved diagnostic cases.

## 5. Add deterministic batch selection
- Extend the audio-enrichment CLI with an inclusive episode-range selection or a dedicated batch argument while retaining the existing repeated `--episode` interface.
- Validate that range bounds are positive, start is not greater than end, and the requested range intersects actual catalogue entries.
- Add a small preparation command or script that reads the current catalogue, selects the requested episodes, partitions them into batches, and emits a compact JSON matrix for GitHub Actions.
- Keep batch size configurable. Start with five episodes per batch and a maximum of four concurrent batch jobs. Measure actual runtimes and provider response behaviour before increasing either value.
- Preserve current scheduled behaviour: select at most five highest-numbered episodes missing verified mappings.
- Preserve manual dry-run as the default and manual write as explicit opt-in.

## 6. Fan out discovery jobs in GitHub Actions
- Add optional inclusive `start_episode` and `end_episode` workflow inputs. If both are empty, retain the existing bounded manual selection. If both are provided, process the inclusive range. Reject a partially supplied range.
- Add bounded `batch_size` and `max_parallel` inputs with safe defaults and upper bounds.
- A preparation job checks out the catalogue, resolves the target episode list, partitions it, and publishes the matrix JSON as a job output.
- A matrix discovery job runs each batch independently with `fail-fast: false`. It invokes the existing enrichment CLI with repeated episode arguments and a unique report path. It never passes `--write`.
- Give every batch a unique artifact name. Upload reports even when a batch fails, using `if: always()`.
- Keep each batch job's timeout explicit. A batch crash must be distinguishable from an individual episode's unresolved result.
- Keep the workflow-level data-write concurrency group so two enrichment runs cannot publish simultaneously. Matrix jobs within one workflow may still run in parallel.
- Keep provider concurrency conservative initially. Do not run one independent job for every episode by default, because that creates unnecessary setup overhead and can amplify provider rate limits.

## 7. Aggregate and publish once
- Add one aggregation job that waits for all matrix jobs and downloads every batch artifact.
- If any batch job failed or a required report is missing, upload the available combined diagnostics but do not publish.
- For a complete run, refresh the latest `origin/main` immediately before applying mappings.
- Merge only entries listed as fully verified in batch reports. Never merge candidate-only or failed episode records.
- If an episode already has a verified mapping, retain it. If the new result differs, report the conflict and do not overwrite the existing verified mapping automatically.
- Validate the complete catalogue and generated exports after merging.
- If write mode is enabled, write and commit the canonical JSON, CSV, metadata, and scrape-report files once from the aggregation job. Do not let matrix jobs write or push.
- If write mode is disabled, retain the combined report as an artifact and leave the canonical catalogue unchanged.
- Keep the existing scheduled write behaviour, and keep manual publication opt-in.

## 8. Reporting and operational visibility
- Produce one combined run report with requested range, selected episode numbers, batch count, concurrency, per-batch status, per-episode stage timings, verified mappings, unresolved reasons, and preserved conflicts.
- Keep each batch report available as a separate artifact for diagnosis.
- Add a GitHub Actions summary showing the total selected, verified, unresolved, failed batches, elapsed time, and publication status.
- Emit warnings for unresolved episodes. Fail the workflow for infrastructure or aggregation failures, not merely because one source lookup is unresolved.
- Record actual timings for preparation, dependency installation, Spotify search, album metadata, YouTube Music discovery, verification, aggregation, and total run.

## 9. Documentation
- Update README manual examples to show a single episode, an inclusive range, and a full catalogue range.
- Update `docs/knowledge/audio-source-catalogue.md` with verified historical artist aliases and the observed release-format rules after live evidence confirms them.
- Document batch size, concurrency defaults, report artifacts, and the single-writer publication model.
- Keep historical request records intact and update the request index.

## 10. Verification and rollout
- Run offline unit tests and catalogue/schema validation first.
- Validate workflow YAML and the generated matrix size for a full 243-episode catalogue.
- Test range boundaries, empty ranges, partial range input, duplicate episode numbers, empty target sets, missing artifacts, failed shards, and conflicting verified mappings.
- Run live Spotify discovery for the historical regression episodes with writes disabled.
- Run a controlled parallel range test with a small number of episodes and compare it with sequential timings.
- Only after the controlled test succeeds, run the full missing or requested catalogue range.
- Publish only after all batch jobs complete and aggregation validation passes.
