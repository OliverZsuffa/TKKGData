# Testing plan: Request 003

1. Inspect the audio enrichment job and confirm FFmpeg installation completes before spotDL runs.
2. Confirm both data-writing workflows use the same concurrency group.
3. Confirm both commit steps rebase origin/main before pushing.
4. Confirm catalogue workflow changes trigger the workflow.
5. Run repository CI and confirm the dataset validation passes.
6. Observe a live audio enrichment run and record its result.
7. Observe a live catalogue refresh and record whether the generated dataset was published.
