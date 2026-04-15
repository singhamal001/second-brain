# Knowledge Gateway Session Update - 2026-04-11

## Session Objective
Enforce Cloudflare Access in front of MCP, enforce app-level Cloudflare gate in the gateway service, and verify that only correctly authenticated external calls can initialize MCP.

## Process Followed
1. Confirmed baseline behavior before hardening:
   - local MCP route reachable with API key.
   - external MCP route reachable via Cloudflare tunnel.
2. Created Cloudflare Access application and attached service-token-based access policy for `mcp.amaxing.site`.
3. Validated expected Access behavior:
   - no Access token => Cloudflare 403.
   - Access token + API key => request reaches origin.
4. Enabled app-level Cloudflare gate in gateway env:
   - `REQUIRE_CLOUDFLARE_ACCESS=true`
   - `ALLOW_CF_BYPASS_FOR_LOCAL=false`
5. Recreated container with updated env and verified local direct MCP request now fails with 403.
6. Diagnosed external 421 errors after Access success and traced to host-header handling for MCP path.
7. Updated Cloudflared ingress host header forwarding to include port for MCP origin path and revalidated initialize flow.

## Confusions Faced
- Difference between Cloudflare Access rejection (403 HTML page) and app-level rejection (403 JSON from FastAPI middleware).
- Why `/health` could pass while `/mcp` returned 421.
- Whether Cloudflare policy path (`/mcp*`) itself caused the 421 (it did not).
- Whether CF service token values should be added to server `.env` (they should not; they are request headers from clients).

## Decisions Taken
- Keep dual-layer auth:
  - Layer 1: Cloudflare Access service token.
  - Layer 2: app API key + client code validation.
- Keep local bypass disabled in production-like mode:
  - `ALLOW_CF_BYPASS_FOR_LOCAL=false`
- Keep tunnel-only exposure pattern with origin bound to localhost.
- Keep Access-protected MCP endpoint as primary integration endpoint for external coding agents.

## Learnings
- 403 and 421 indicate different failure planes:
  - 403 (Cloudflare page): blocked at Access edge.
  - 421: origin host-header mismatch for MCP transport security.
- Health endpoint success does not guarantee MCP transport success; always test MCP initialize directly.
- App-level Cloudflare gate and Cloudflare Access are complementary, not redundant.

## Line Items Achieved
1. Cloudflare Access service-token guard is active for MCP endpoint.
2. App-level Cloudflare gate is enabled and enforced.
3. Local direct `/mcp` calls are blocked as expected.
4. External Access-authenticated `/health` calls succeed.
5. MCP initialize over external endpoint succeeds after host-header correction.
6. Security posture moved from "functional MVP" to "hardened MVP path".

## Partially Completed
1. API key rotation remains pending (deferred by choice).
2. Cloudflare policy scope finalization (`/mcp*` vs `/*`) pending based on whether `/docs` and `/health` should also be protected for all users.
3. Client onboarding docs for non-curl agent clients pending (Codex/Claude/Cursor templates).

## Backlog
1. Rotate API key and revoke old key after current integration cycle.
2. Add `docker-compose.yml` for deterministic VPS restarts and env management.
3. Add explicit external-client integration docs for MCP initialize/notifications/tool-call flow.
4. Decide final Access app path scope and browser access policy strategy.
5. Add automated smoke test script for:
   - initialize
   - tools/list
   - create_project flow
   - Obsidian note path existence.

## Verified Production-Like State
- `REQUIRE_CLOUDFLARE_ACCESS=true`
- `ALLOW_CF_BYPASS_FOR_LOCAL=false`
- Cloudflare Access service-token policy active.
- Cloudflared ingress includes explicit host-header forwarding for MCP origin.

## Session Closure Note (End of Work Block)
- Completed today:
  - Cloudflare Access + app-level gate hardening validated.
  - MCP tool metadata/usage playbook upgrade deployed and verified live.
  - Cleanup reset executed for Supabase app data and Obsidian project data.
- Explicit next-session start point:
  - onboard external coding agents to this MCP endpoint, starting with Codex and Claude Code.
  - run end-to-end agent logging flow against fresh data.
