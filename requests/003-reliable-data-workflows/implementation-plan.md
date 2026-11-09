# Implementation plan: Reliable data workflows

**Status:** Approved. Implementation in progress.

1. Install FFmpeg on the Ubuntu runner before spotDL and audio enrichment dependencies.
2. Use the same GitHub Actions concurrency group for catalogue refresh and audio enrichment.
3. Rebase the generated data commit on origin/main before pushing.
4. Include the catalogue workflow file in its own push path filter so workflow changes can be exercised immediately.
5. Preserve validation before the commit step and report artifacts on failure.
6. Verify workflow runs after merge and inspect actual publication outcomes.
