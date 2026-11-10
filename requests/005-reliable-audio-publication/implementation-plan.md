# Implementation plan: Reliable audio enrichment publication

**Status:** Awaiting approval.

## Problem

The audio discovery run for episode 149 verified all 40 Spotify tracks and all 40 YouTube Music tracks, but publication failed during `git pull --rebase origin main`. The workflow had generated its data changes from an older checkout. The rebase then conflicted in the four generated catalogue files, so the verified mappings were never pushed.

## Findings in the current workflows

Both catalogue writing workflows already share the `tkkgdata-data-writes` concurrency group with cancellation disabled. The catalogue refresh workflow checks out `main`. The audio enrichment workflow refreshes its checkout only for scheduled runs. A manually dispatched write run can therefore continue from the commit associated with the dispatch event instead of the latest `main`.

## Proposed changes

1. Keep the shared concurrency group so catalogue refresh and audio enrichment cannot publish simultaneously.
2. Before any audio enrichment run that will write data, fetch `origin/main` and reset the checkout to that latest commit. This must happen after the workflow has entered its concurrency slot and before discovery starts. Scheduled runs continue to refresh as they do now. Manual runs with the write input enabled receive the same protection.
3. Keep the final fetch and rebase before pushing as a last safety check. Do not force push, discard remote changes, or automatically resolve conflicts by choosing one side.
4. Make the workflow summary and logs clearly distinguish successful discovery from successful publication, so a verified report cannot be mistaken for a published catalogue update.
5. Add or update lightweight workflow tests or validation where the existing test setup supports it. Validate the workflow YAML and confirm both write workflows retain the shared concurrency group.
6. After the fix is merged, rerun audio enrichment for episode 149 with writing enabled. Confirm the resulting commit contains the verified mappings and that the canonical catalogue retains all 40 track pairs.

## Scope and safety

Only workflow publication behavior and its tests or documentation will change. Do not alter discovery matching rules, episode metadata, or special case handling for any episode. Do not modify the canonical dataset as part of this implementation. Episode 149 will be republished only in the post-merge verification run.

## Acceptance criteria

- A manually dispatched audio enrichment write starts from the latest `main` after waiting for the shared concurrency group.
- Scheduled audio enrichment continues to start from the latest `main`.
- Catalogue refresh and audio enrichment remain serialized.
- No force push or destructive conflict resolution is introduced.
- A successful episode 149 discovery is committed to `main`, and the published episode has all 40 verified Spotify and YouTube Music track pairs.
- The workflow reports publication failure clearly if the final push cannot be completed.
