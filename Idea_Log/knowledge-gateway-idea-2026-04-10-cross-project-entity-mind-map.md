# Idea Log - 2026-04-10
## Title
Cross-Project Entity Mind Map Generator (Daily Cron)

## Context
We are already storing project memory in two places:
- Structured: Postgres/Supabase tables
- Unstructured: Obsidian markdown notes

The idea is to add a daily job that reads newly added/updated notes and records, then builds or updates a cross-project mind map in Obsidian.

## Core Idea
Create a scheduled process (daily) that:
1. Scans newly created/updated artifacts from both systems.
2. Extracts entities (tools, services, frameworks, people, domains, patterns, decisions).
3. Builds relationships between entities and projects.
4. Outputs a graph/mind-map style markdown artifact inside a dedicated Obsidian folder.

## Example
- Project A contains work on AWS Lambda.
- Project B contains work on AWS EC2.
- System should connect both under a shared entity: AWS.
- Mind map should show where AWS is used, why, and linked artifacts/notes across projects.

## Proposed Obsidian Location
- `Knowledge_Graph/` (or similar dedicated folder outside specific project folders)
- Suggested files:
  - `Knowledge_Graph/daily-entity-map-YYYY-MM-DD.md`
  - `Knowledge_Graph/entity-index.md`

## Potential Outputs
- Entity summary table (entity, type, first seen, last seen, projects).
- Relationship graph in markdown (links/tags/frontmatter).
- Top recurring patterns and cross-project reusable approaches.

## Why This Is Valuable
- Improves cross-project recall and reuse.
- Surfaces transferable patterns and architecture choices.
- Converts raw logs into second-brain intelligence.

## Candidate Future Scope (when prioritized)
- Daily cron/automation worker.
- Entity extraction pipeline (rules first, optional NLP later).
- Incremental update mode (process only new delta since last run).
- Confidence scoring for extracted links.

## Status
- Stage: Idea Logged
- Priority: Backlog Candidate
- Implement Now: No (defer until core MCP logging/retrieval flow is fully stable)
