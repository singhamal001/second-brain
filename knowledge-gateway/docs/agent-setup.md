# Multi-Agent MCP Setup Guide

## Goal
Connect multiple coding agents (Codex, Claude Code, Gemini CLI, Cursor) to the same VPS MCP endpoint so they all write/read from one Obsidian + Supabase memory system.

## Shared Values (All Agents)
- MCP URL: `https://mcp.amaxing.site/mcp`
- Required headers:
  - `CF-Access-Client-Id`
  - `CF-Access-Client-Secret`
  - `Authorization: Bearer <KG_API_KEY>`
  - `X-Client-Code: <KG_CLIENT_CODE>`

## Recommended Environment Variables
Define these per machine:
- `KG_MCP_URL`
- `CF_ACCESS_CLIENT_ID`
- `CF_ACCESS_CLIENT_SECRET`
- `KG_API_KEY`
- `KG_CLIENT_CODE`

Linux/macOS (shell profile example):
```bash
export KG_MCP_URL="https://mcp.amaxing.site/mcp"
export CF_ACCESS_CLIENT_ID="..."
export CF_ACCESS_CLIENT_SECRET="..."
export KG_API_KEY="..."
export KG_CLIENT_CODE="1234567890"
```

Windows PowerShell (current session):
```powershell
$env:KG_MCP_URL="https://mcp.amaxing.site/mcp"
$env:CF_ACCESS_CLIENT_ID="..."
$env:CF_ACCESS_CLIENT_SECRET="..."
$env:KG_API_KEY="..."
$env:KG_CLIENT_CODE="1234567890"
```

## 1) Codex
Codex MCP config is stored in:
- user scope: `~/.codex/config.toml`
- project scope: `.codex/config.toml`

Add server (recommended via config file for custom headers):
```toml
[mcp_servers.knowledge_gateway]
url = "https://mcp.amaxing.site/mcp"

[mcp_servers.knowledge_gateway.env_http_headers]
CF-Access-Client-Id = "CF_ACCESS_CLIENT_ID"
CF-Access-Client-Secret = "CF_ACCESS_CLIENT_SECRET"
Authorization = "KG_AUTH_HEADER"
X-Client-Code = "KG_CLIENT_CODE"
```

Set helper env var before launch:
```bash
export KG_AUTH_HEADER="Bearer $KG_API_KEY"
```

Verify:
```bash
codex mcp list
```

## 2) Claude Code
Claude supports MCP via CLI and config scopes.
- local/user scopes are stored in `~/.claude.json`
- project scope writes `.mcp.json` in repo root

Recommended (project scope + env expansion):
```json
{
  "mcpServers": {
    "knowledge_gateway": {
      "type": "http",
      "url": "${KG_MCP_URL}",
      "headers": {
        "CF-Access-Client-Id": "${CF_ACCESS_CLIENT_ID}",
        "CF-Access-Client-Secret": "${CF_ACCESS_CLIENT_SECRET}",
        "Authorization": "Bearer ${KG_API_KEY}",
        "X-Client-Code": "${KG_CLIENT_CODE}"
      }
    }
  }
}
```

Quick checks:
```bash
claude mcp list
claude mcp get knowledge_gateway
```
Inside Claude Code: `/mcp`

## 3) Gemini CLI
Gemini MCP config is stored in:
- user scope: `~/.gemini/settings.json`
- project scope: `.gemini/settings.json`

Add server with CLI:
```bash
gemini mcp add --scope user --transport http knowledge_gateway "$KG_MCP_URL" \
  --header "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
  --header "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
  --header "Authorization: Bearer $KG_API_KEY" \
  --header "X-Client-Code: $KG_CLIENT_CODE"
```

Verify:
```bash
gemini mcp list
```

Note:
- Gemini stores server config in `settings.json`. Treat that file as secret-bearing config and lock file permissions.

## 4) Cursor
Cursor MCP config is in `mcp.json`.
- macOS/Linux: `~/.cursor/mcp.json`
- Windows: `%USERPROFILE%\\.cursor\\mcp.json`

Example:
```json
{
  "mcpServers": {
    "knowledge_gateway": {
      "url": "${KG_MCP_URL}",
      "headers": {
        "CF-Access-Client-Id": "${CF_ACCESS_CLIENT_ID}",
        "CF-Access-Client-Secret": "${CF_ACCESS_CLIENT_SECRET}",
        "Authorization": "Bearer ${KG_API_KEY}",
        "X-Client-Code": "${KG_CLIENT_CODE}"
      }
    }
  }
}
```

If your Cursor build does not expand `${VAR}` in `mcp.json`, replace those values with literal header values.

Verify via CLI:
```bash
cursor-agent mcp list
cursor-agent mcp list-tools knowledge_gateway
```

## Universal Connectivity Smoke Test
Use this from any machine to validate credentials and path:
```bash
curl --http1.1 -sS -i -X POST "$KG_MCP_URL" \
  -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
  -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
  -H "Authorization: Bearer $KG_API_KEY" \
  -H "X-Client-Code: $KG_CLIENT_CODE" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke","version":"1.0"}}}'
```

Expected:
- `HTTP 200`
- `mcp-session-id` present

## Behavior Policy (All Agents)
Put this in each agent's system/custom instructions:
1. Use `create_employer` and `create_project` to establish context.
2. Use `log_coding_session`, `log_meeting`, `log_decision` for canonical writes.
3. Use `upsert_obsidian_note` only when explicit custom note behavior is requested.
4. Always include `idempotency_key` for session logging.

## Skill Pull + Cache Policy (All Agents)
1. At session start, call `get_usage_playbook` once and cache by `version`.
2. Call `list_gateway_skills` and fetch only required skills via `get_gateway_skill`.
3. Do not fetch all skills for every prompt; load only skill docs required by current intent.
4. Respect router defaults from playbook:
   - `scope_resolution_policy = ask_if_missing`
   - `unknown_intent_policy = clarify_then_proceed`
   - DB-intent `create database -> create_dynamic_table`
5. For shared updates, use `update_gateway_skill` (or logging wrappers for legacy flow).

## References
- OpenAI Codex MCP docs: https://developers.openai.com/codex/mcp
- OpenAI Docs MCP quickstart (Codex/Cursor examples): https://developers.openai.com/learn/docs-mcp
- Claude Code MCP docs: https://code.claude.com/docs/en/mcp
- Gemini CLI repository README (MCP + settings path): https://github.com/google-gemini/gemini-cli
