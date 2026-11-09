# TKKGData project instructions

## Start here
Before planning or changing the project, read:
1. README.md
2. docs/README.md
3. docs/knowledge/README.md and relevant topics
4. docs/decisions.md
5. The active request's request.md, implementation-plan.md, testing.md, and notes.md

## Request and approval workflow
All substantial work must have a numbered request folder under requests/. Each request contains request.md, implementation-plan.md, testing.md, notes.md, and optional attachments/.

Investigate only what is needed, write the request and plan, present the plan, and wait for Oliver's explicit approval before implementation. Approval authorizes only the stated scope. If a material change becomes necessary, explain it and obtain approval before proceeding.

After approval, work on a focused feature branch. Run relevant tests and validation, review the diff, and document actual results. Never claim a check ran unless it actually ran. Do not force-push, merge, or deploy without Oliver's explicit approval. Preserve the user's test observations and do not mark a request complete on their behalf.

## Knowledge base
Reusable architecture and verified lessons belong in docs/knowledge/. Request-specific plans, open questions, and test results stay in the request folder. Only explicitly approved durable decisions belong in docs/decisions.md. Update existing knowledge where possible and do not record proposals as facts.

## Data integrity
- TKKGData is the sole authoritative owner of the published TKKG dataset and its schema.
- Consumers must not scrape sources or maintain competing copies of episode metadata.
- Never invent episode facts, provider IDs, track links, dates, or relationships.
- Preserve source provenance, retrieval time, and verification status for sourced claims.
- Distinguish candidates, verified facts, curated corrections, and unresolved conflicts.
- A failed source must not erase previously verified data.
- A source outage must not publish an incomplete or invalid replacement dataset.
- Keep archive chapter segmentation distinct from streaming album track divisions.
- Keep user-specific listening progress, favourites, settings, and download preferences out of this repository.
- Respect robots.txt, source terms, access restrictions, conservative request rates, and caching. Never bypass authentication or access controls.

## Engineering
Prefer small source adapters, deterministic normalization, explicit validation, and reproducible builds. Keep raw/source evidence separate from normalized published records. Add fixtures for source parsing and regression cases. Make network discovery optional to offline validation and tests. Pin and justify dependencies. Do not commit credentials, cookies, personal data, downloaded audio, or generated temporary files.
