# Knowledge Gateway Task Plan - 2026-04-11

## Objective
Standardize cross-agent MCP usage so Codex, Claude Code, Gemini CLI, and Cursor can reliably write/read from one VPS-hosted Obsidian + Supabase memory system.

## Task 1 - Improve Server Side For Better MCP Understanding
- Add strong descriptions for each MCP tool:
  - when to use
  - when not to use
  - required arguments
  - expected output shape
- Add a policy/tooling guidance endpoint (for example `get_usage_playbook`) so agents can fetch canonical usage rules.
- Mark `upsert_obsidian_note` as advanced/manual-only tool.
- Add validation rules for standardized session logging inputs.
- Add/update tests to ensure tool metadata and policy outputs remain present and stable.

## Task 2 - Step-By-Step Setup Docs For Major Coding Agents
- Create manual (no script) onboarding docs for:
  - Codex
  - Claude Code
  - Gemini CLI
  - Cursor
- For each agent include:
  - where to store environment variables on secure machines
  - where to add MCP server URL and headers
  - minimal initialize/tools-list verification flow
  - troubleshooting notes for 401/403/421/500
- Include examples with placeholder values for:
  - `CF-Access-Client-Id`
  - `CF-Access-Client-Secret`
  - `Authorization: Bearer <api_key>`
  - `X-Client-Code`

## Task 3 - Define A Standard Skill For Logging
- Design a strict "log this session" standard:
  - required vs optional fields
  - idempotency-key pattern
  - canonical note structure
  - terminology mapping ("log session", "log decision", "log meeting")
- Create a reusable skill spec that tells agents exactly how to interpret logging intents.
- Add canonical examples for:
  - coding session
  - meeting
  - decision

## Recommended Execution Order
1. Task 3 (define standard and skill first).
2. Task 1 (encode standard in MCP server descriptions/validation).
3. Task 2 (publish platform-specific setup docs based on finalized standard).

## Definition Of Done
- All listed coding agents can connect to the same MCP endpoint using documented manual steps.
- Agent behavior is consistent for structured logging operations.
- Obsidian and Supabase writes follow one canonical format/path model.
- Free-form note writing is constrained and clearly documented.
