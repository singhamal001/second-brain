# Universal Skill Suite + Router Protocol

## Objective
Provide one centralized, MCP-hosted skill system so any coding agent uses Knowledge Gateway tools consistently with minimal token waste.

## Skill Architecture
Split skills (source of truth in vault):
- `knowledge-gateway-router`
- `knowledge-gateway-logging`
- `knowledge-gateway-schema-intake`

Canonical vault paths:
- `System/Skills/knowledge-gateway-router/SKILL.md`
- `System/Skills/knowledge-gateway-logging/SKILL.md`
- `System/Skills/knowledge-gateway-schema-intake/SKILL.md`

## MCP Skill Management Contract
Generic tools:
- `list_gateway_skills()`
- `get_gateway_skill(skill_name)`
- `initialize_gateway_skill(skill_name, force=false)`
- `initialize_gateway_skills(force=false)`
- `update_gateway_skill(skill_name, content, mode, reason?)`

Backward-compatible wrappers:
- `get_logging_skill()`
- `initialize_logging_skill(force=false)`
- `update_logging_skill(content, mode, reason?)`

## Router Protocol (Deterministic)
1. Call `get_usage_playbook` once per session and cache by `version`.
2. Resolve intent + scope.
3. If scope is missing, ask one batched clarification.
4. Route to one canonical tool.
5. Skip redundant `tools/list` calls once mapping is known.

## DB Intent Mapping
- Phrase: "create database"
- Canonical route: `create_dynamic_table`
- Required clarification bundle when missing:
  - scope
  - table purpose
  - columns + types

## Scope and Naming Policy
Scope model:
- `global`
- `employer_all_projects`
- `single_project`
- `multi_employer_or_multi_project`

Table naming policy: `auto_prefix_by_scope`
- global: `global_<name>`
- employer: `<employer_slug>_<name>`
- project: `<employer_slug>_<project_slug>_<name>`

## Ambiguity and Safety
- Unknown intent policy: `clarify_then_proceed`
- No write tool call should be emitted while intent remains ambiguous.
- Non-destructive model remains enforced (`archive` instead of delete/drop).
