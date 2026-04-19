# Skill: knowledge-gateway-logging

## Version
2026-04-19

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
- Example: `codex-lenovo-20260419T160000Z-001`

## Checksum Discipline
- Treat this document as versioned policy.
- Before replacing content, compare checksum via `get_gateway_skill`.
- Include update reason when using `update_gateway_skill`.

## Verification Checklist
After every structured write:
1. Confirm `status == success`
2. Save `operation_id`
3. Capture `obsidian_note_path` when relevant
4. If retrying, reuse the same `idempotency_key`
