# Codex Instances Setup (Shared VPS MCP)

## Purpose
Use the same `knowledge-gateway` MCP endpoint from any Codex installation (any machine) with per-machine identity and shared memory behavior.

## Architecture (Simple)
1. Codex on Machine A/B/C calls `https://mcp.amaxing.site/mcp`.
2. Cloudflare Access validates service token.
3. Gateway validates API key + client code.
4. Gateway writes to one Supabase DB + one Obsidian vault.

## 0) Prerequisites
- VPS gateway is running and healthy.
- Cloudflare Access app + service token exists for `mcp.amaxing.site`.
- You have a gateway API key and client code pair for this machine.

## 1) Create Per-Machine Client Identity (VPS)
Run this on VPS to create a unique client code + API key for each machine:

```bash
docker exec -it knowledge-gateway python scripts/provision_client.py \
  --client-code 9200010001 \
  --label codex-amal-lenovo-rtx3060
```

Notes:
- Keep `client_code` unique per machine.
- You may use different API keys per machine (recommended).

## 2) Set Secrets On The Machine Running Codex

### Windows PowerShell
```powershell
$env:KG_MCP_URL="https://mcp.amaxing.site/mcp"
$env:CF_ACCESS_CLIENT_ID="<cloudflare-access-client-id>"
$env:CF_ACCESS_CLIENT_SECRET="<cloudflare-access-client-secret>"
$env:KG_API_KEY="<knowledge-gateway-api-key>"
$env:KG_CLIENT_CODE="9200010001"
$env:KG_AUTH_HEADER="Bearer $env:KG_API_KEY"
```

### Linux/macOS
```bash
export KG_MCP_URL="https://mcp.amaxing.site/mcp"
export CF_ACCESS_CLIENT_ID="<cloudflare-access-client-id>"
export CF_ACCESS_CLIENT_SECRET="<cloudflare-access-client-secret>"
export KG_API_KEY="<knowledge-gateway-api-key>"
export KG_CLIENT_CODE="9200010001"
export KG_AUTH_HEADER="Bearer $KG_API_KEY"
```

## 3) Add MCP Server To Codex Config
Codex config path:
- Windows: `C:\Users\<you>\.codex\config.toml`
- Linux/macOS: `~/.codex/config.toml`

Add:

```toml
[mcp_servers.knowledge_gateway]
url = "https://mcp.amaxing.site/mcp"

[mcp_servers.knowledge_gateway.env_http_headers]
CF-Access-Client-Id = "CF_ACCESS_CLIENT_ID"
CF-Access-Client-Secret = "CF_ACCESS_CLIENT_SECRET"
Authorization = "KG_AUTH_HEADER"
X-Client-Code = "KG_CLIENT_CODE"
```

Restart Codex after editing config.

## 4) Connectivity Smoke Test (Machine Local)
Run before opening a long session:

```bash
curl --http1.1 -sS -i -X POST "$KG_MCP_URL" \
  -H "CF-Access-Client-Id: $CF_ACCESS_CLIENT_ID" \
  -H "CF-Access-Client-Secret: $CF_ACCESS_CLIENT_SECRET" \
  -H "Authorization: Bearer $KG_API_KEY" \
  -H "X-Client-Code: $KG_CLIENT_CODE" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"codex-smoke","version":"1.0"}}}'
```

Expected:
- `HTTP 200`
- `mcp-session-id` header present

## 5) Initialize Shared Logging Skill Once
From any agent connected to MCP:
1. Call `initialize_logging_skill`.
2. Call `get_logging_skill` to verify content/path.

Canonical skill path in vault:
- `System/Skills/knowledge-gateway-logging/SKILL.md`

## 6) Recommended Agent Behavior
1. Use `create_employer` and `create_project` for context.
2. Use `log_coding_session`/`log_meeting`/`log_decision` for canonical writes.
3. Use `upsert_obsidian_note` only for explicit manual/custom notes.
4. Use `idempotency_key` for reliable retries.

