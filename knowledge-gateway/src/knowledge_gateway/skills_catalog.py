from __future__ import annotations

LOGGING_SKILL_NAME = "knowledge-gateway-logging"
LOGGING_SKILL_VERSION = "2026-04-16"
LOGGING_SKILL_CANONICAL_PATH = "System/Skills/knowledge-gateway-logging/SKILL.md"

DEFAULT_LOGGING_SKILL_CONTENT = """# Skill: knowledge-gateway-logging

## Purpose
Turn raw development activity into durable second-brain memory with consistent structure across projects, devices, and agents.

## Golden Rule
Prefer structured gateway tools over ad-hoc markdown writes.

## Intent Routing
1. "log this session" -> `log_coding_session`
2. "log meeting" -> `log_meeting`
3. "log decision" -> `log_decision`
4. "show project summary/timeline/dependencies" -> reporting tools
5. Use `upsert_obsidian_note` only for explicit custom/manual notes outside structured schemas.

## Session Logging Standard
Required fields:
- `employer_name`
- `project_name`
- `session_title`
- `idempotency_key`
- `started_at` (ISO-8601)

Highly recommended fields:
- `summary`
- `major_changes`
- `blockers`
- `next_steps`
- `learnings`
- `tags`

## Idempotency Standard
- Reuse the same `idempotency_key` for retries/replays of one logical write.
- Recommended format: `<agent>-<machine>-<utcstamp>-<seq>`
- Example: `codex-lenovo-20260416T143000Z-001`

## Quality Bar
1. Write factual summaries, not vague status lines.
2. Record concrete next steps and owners where possible.
3. Keep terminology stable (`aws-lambda`, `cloudflare-access`, `mcp-auth`) for better retrieval.
4. Prefer short reusable tags in lowercase.

## Safety Model
1. Do not use destructive data flows.
2. Use archive semantics (`archive_rows`, `archive_table`) for removal intent.
3. Do not bypass gateway constraints with raw SQL behavior.

## Verification Checklist
After every structured write:
1. Confirm `status == success`
2. Save `operation_id`
3. Capture `obsidian_note_path` when relevant
4. If retrying, reuse the same `idempotency_key`

## Retrieval Habits
For "what did we do before?":
1. `get_project_timeline` for chronology
2. `get_project_summary` for aggregate context
3. `get_open_dependencies` for blockers
4. `get_obsidian_note` when exact note path is known
"""

