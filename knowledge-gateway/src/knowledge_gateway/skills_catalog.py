from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GatewaySkillSpec:
    name: str
    version: str
    canonical_path: str
    default_content: str


LOGGING_SKILL_NAME = "knowledge-gateway-logging"
ROUTER_SKILL_NAME = "knowledge-gateway-router"
SCHEMA_INTAKE_SKILL_NAME = "knowledge-gateway-schema-intake"

LOGGING_SKILL_VERSION = "2026-04-19"
ROUTER_SKILL_VERSION = "2026-04-19"
SCHEMA_INTAKE_SKILL_VERSION = "2026-04-19"

LOGGING_SKILL_CANONICAL_PATH = "System/Skills/knowledge-gateway-logging/SKILL.md"
ROUTER_SKILL_CANONICAL_PATH = "System/Skills/knowledge-gateway-router/SKILL.md"
SCHEMA_INTAKE_SKILL_CANONICAL_PATH = "System/Skills/knowledge-gateway-schema-intake/SKILL.md"

DEFAULT_LOGGING_SKILL_CONTENT = """# Skill: knowledge-gateway-logging

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
"""

DEFAULT_ROUTER_SKILL_CONTENT = """# Skill: knowledge-gateway-router

## Version
2026-04-19

## Purpose
Resolve user intent to the correct gateway tool with minimum token usage and safe clarification behavior.

## Session Bootstrap
1. Call `get_usage_playbook` once per session.
2. Cache by playbook `version`.
3. Do not re-fetch playbook unless session reset or version mismatch.

## Intent Router Protocol
1. Detect write vs read intent.
2. Resolve scope: `global`, `employer_all_projects`, `single_project`, `multi_employer_or_multi_project`.
3. If critical scope is missing, ask one consolidated clarification question.
4. Route to one canonical tool.
5. Avoid redundant tool-discovery/list calls once mapped.

## Unknown Intent Policy
- Policy: `clarify_then_proceed`
- Do not emit write tool calls on ambiguous intents.
- Ask one targeted question that captures scope + objective + required fields.

## Router Mapping Highlights
- "create database" -> `create_dynamic_table` (schema-intake policy applies)
- "log this session" -> `log_coding_session`
- "log meeting" -> `log_meeting`
- "log decision" -> `log_decision`
- "show timeline" -> `get_project_timeline`
- "show summary" -> `get_project_summary`

## Checksum Discipline
- Verify current skill checksum before local caching.
- Replace local cache only when version/checksum changes.
"""

DEFAULT_SCHEMA_INTAKE_SKILL_CONTENT = """# Skill: knowledge-gateway-schema-intake

## Version
2026-04-19

## Purpose
Handle prompts like "create a database/table" using safe dynamic-table workflows in the existing KG Postgres.

## Canonical Mapping
- "create database" means `create_dynamic_table`.
- Never provision external database infrastructure from this intent.

## Clarification Batch (ask once if missing)
1. Scope: global / employer / project / cross-employer
2. Table purpose (business intent)
3. Required columns and types

## Scope Model
- `global`
- `employer_all_projects`
- `single_project`
- `multi_employer_or_multi_project`

## Table Naming Policy (auto_prefix_by_scope)
- global: `global_<name>`
- employer: `<employer_slug>_<name>`
- project: `<employer_slug>_<project_slug>_<name>`

## Column Safety
- Use gateway-supported types only: text/string/int/float/bool/datetime/json.
- Avoid reserved metadata columns (`id`, `created_at`, `updated_at`, `archived`).

## Checksum Discipline
- Treat this as strict policy text.
- Update through `update_gateway_skill` with reason.
"""


SKILL_SPECS: dict[str, GatewaySkillSpec] = {
    LOGGING_SKILL_NAME: GatewaySkillSpec(
        name=LOGGING_SKILL_NAME,
        version=LOGGING_SKILL_VERSION,
        canonical_path=LOGGING_SKILL_CANONICAL_PATH,
        default_content=DEFAULT_LOGGING_SKILL_CONTENT,
    ),
    ROUTER_SKILL_NAME: GatewaySkillSpec(
        name=ROUTER_SKILL_NAME,
        version=ROUTER_SKILL_VERSION,
        canonical_path=ROUTER_SKILL_CANONICAL_PATH,
        default_content=DEFAULT_ROUTER_SKILL_CONTENT,
    ),
    SCHEMA_INTAKE_SKILL_NAME: GatewaySkillSpec(
        name=SCHEMA_INTAKE_SKILL_NAME,
        version=SCHEMA_INTAKE_SKILL_VERSION,
        canonical_path=SCHEMA_INTAKE_SKILL_CANONICAL_PATH,
        default_content=DEFAULT_SCHEMA_INTAKE_SKILL_CONTENT,
    ),
}


def list_skill_specs() -> list[GatewaySkillSpec]:
    return [SKILL_SPECS[name] for name in sorted(SKILL_SPECS)]


def get_skill_spec(skill_name: str) -> GatewaySkillSpec | None:
    return SKILL_SPECS.get(skill_name)

