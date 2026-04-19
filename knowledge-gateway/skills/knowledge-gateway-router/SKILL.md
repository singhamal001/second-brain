# Skill: knowledge-gateway-router

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
