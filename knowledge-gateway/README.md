# Knowledge Gateway

Unified VPS-hosted MCP gateway for Obsidian vault + Supabase/Postgres.

## Features
- Streamable HTTP MCP endpoint at `/mcp`
- Cloudflare + API key auth middleware
- Dual-write logging (structured DB + Obsidian markdown)
- Dynamic table creation with non-destructive archival model
- Audited mutations via `activity_log`
- Obsidian path convention: `Employers/<Employer>/<Project>/<YYYY-MM-DD-update-feature>/...`

## Quickstart
1. Create env:
   - Copy `.env.example` to `.env`
   - Set `DATABASE_URL`, `VAULT_ROOT`, `API_KEY_PEPPER`
2. Install:
   - `pip install -e .[test]`
3. Run:
   - `uvicorn knowledge_gateway.app:create_app --factory --host 0.0.0.0 --port 8080`
4. Health:
   - `GET /health`

## Auth
- `Authorization: Bearer <api_key>` required for `/mcp`
- Optional `X-Client-Code: <10-digit>`
- Optional Cloudflare Access header enforcement via env

## Non-destructive policy
- No drop/delete tools are exposed
- Tables can be archived in `table_registry`
- Rows archived by setting `archived=1`

## Tests
- `pytest -q`

## Agent Guidance
- Logging standard: `docs/logging-standard.md`
- Reusable logging skill spec: `skills/knowledge-gateway-logging/SKILL.md`
- Skill-suite MCP tools:
  - `list_gateway_skills`
  - `get_gateway_skill`
  - `initialize_gateway_skill`
  - `initialize_gateway_skills`
  - `update_gateway_skill`
- Backward-compatible logging wrappers:
  - `get_logging_skill`
  - `initialize_logging_skill`
  - `update_logging_skill`
- Skill suite architecture: `docs/architecture/skill-suite-router-protocol.md`
- Codex multi-machine setup: `docs/setup/codex-instances-setup.md`
- GHCR release/deploy runbook: `docs/deploy/ghcr-rebuild-push-pull.md`
