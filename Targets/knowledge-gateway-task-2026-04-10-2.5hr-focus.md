# Knowledge Gateway Task Plan - 2026-04-10 (2.5 Hour Focus Session)

## Session Goal
Close all critical backlog items needed for production-ready MCP usage:
- secure auth state,
- validated end-to-end MCP tool flow,
- verified Obsidian dual-write output,
- hardened external access controls.

## Definition of Done (Must Complete)
1. API key rotated and old key confirmed invalid.
2. MCP workflow validated end-to-end after initialize:
   - `tools/list`
   - `create_employer`
   - `create_project`
   - `log_coding_session`
3. Obsidian note creation verified in mounted vault path format:
   - `Employers/<Employer>/<Project>/<YYYY-MM-DD-update-...>/...`
4. Cloudflare Access hardening completed and app env toggles aligned:
   - `REQUIRE_CLOUDFLARE_ACCESS=true`
   - `ALLOW_CF_BYPASS_FOR_LOCAL=false`

## Timebox Plan (150 Minutes)

### Phase 1 (0-25 min): Security Hygiene + Baseline Validation
- Rotate API key:
  - `docker exec -it knowledge-gateway python scripts/provision_client.py --client-code 1234567890 --label codex-rotated-2026-04-10`
- Confirm baseline health:
  - `curl -i http://127.0.0.1:8080/health`
  - `curl -i https://mcp.amaxing.site/health`
- Validate old key rejection (`401`) and new key acceptance path.

### Phase 2 (25-80 min): MCP Smoke Flow (Protocol-Correct)
- Initialize MCP session and capture `mcp-session-id`.
- Send `notifications/initialized`.
- Run `tools/list`.
- Run mutation tools in order:
  - `create_employer`
  - `create_project`
  - `log_coding_session`
- Capture and store response payloads for evidence.

### Phase 3 (80-110 min): Dual-Write Verification (DB + Obsidian)
- Confirm new records exist in Supabase tables (`employers`, `projects`, `sessions`, `activity_log`).
- Verify Obsidian file was created under expected path in mounted vault:
  - `/opt/obsidian/vault/knowledge-gateway/Employers/...`
- Validate file content includes session title/summary fields.

### Phase 4 (110-140 min): Hardening
- Enable strict Cloudflare requirement in `/opt/knowledge-gateway/.env`:
  - `REQUIRE_CLOUDFLARE_ACCESS=true`
  - `ALLOW_CF_BYPASS_FOR_LOCAL=false`
- Restart container.
- Validate:
  - no Cloudflare header => denied
  - with Cloudflare path + app key => allowed

### Phase 5 (140-150 min): Closeout Logging
- Update tracker with:
  - line items achieved,
  - unresolved items,
  - commands/output references.
- If time remains: draft `docker-compose.yml` backlog stub.

## Command Snippets (Ready to Use)
```bash
# Check container image and health
docker inspect knowledge-gateway --format '{{.Config.Image}}'
curl -i http://127.0.0.1:8080/health
curl -i https://mcp.amaxing.site/health

# Initialize MCP
curl --http1.1 -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "X-Client-Code: 1234567890" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1.0"}}}'

# After getting mcp-session-id, send initialized + tools/list
curl --http1.1 -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "Authorization: Bearer <API_KEY>" \
  -H "X-Client-Code: 1234567890" \
  -H "mcp-session-id: <SESSION_ID>" \
  -H "mcp-protocol-version: 2025-03-26" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"tools-1","method":"tools/list","params":{}}'
```

## Risks to Watch
- Shell quoting mistakes in curl headers/body causing false negatives.
- Using stale/old API key while testing new auth behavior.
- Confusing Cloudflare-level denial with app-level denial.

## Success Evidence Checklist
- Screenshot/log of successful `initialize` response.
- Tool invocation outputs for `create_employer`, `create_project`, `log_coding_session`.
- Filesystem proof of generated Obsidian note path.
- Confirmation that old API key fails and new key succeeds.
