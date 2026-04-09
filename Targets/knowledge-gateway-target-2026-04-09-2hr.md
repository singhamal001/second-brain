# 2026-04-09 | 2-Hour Execution Target

## Context Carry-Forward
We are resuming from the last blocker:
- `knowledge-gateway` image is built and pulled from GHCR on VPS.
- Container failed to start because DB connection used direct Supabase DB host (IPv6 route issue).
- Supabase has SSL-only connections enabled.

## 2-Hour Target (Definition of Done)
By the end of 2 hours, achieve all of the following:
1. `knowledge-gateway` container is running successfully on VPS.
2. `/health` returns `200` on `127.0.0.1:8080`.
3. Supabase connectivity is confirmed using Pooler DSN + `sslmode=require`.
4. First API client key is provisioned from inside the running container.
5. MCP endpoint is reachable through Cloudflare tunnel hostname (or fully prepared if DNS propagation is pending).

---

## Timeboxed Plan (120 mins)

### 0-20 mins: Fix Env and Start Container
- Update `/opt/knowledge-gateway/.env` with **Supabase Pooler** `DATABASE_URL`.
- Ensure DSN includes `?sslmode=require`.
- URL-encode DB password if needed (`@` -> `%40`, etc.).
- Recreate container with vault mount:
  - host: `/opt/obsidian/vault`
  - container: `/data/vault`
  - app root: `VAULT_ROOT=/data/vault/knowledge-gateway`

### 20-40 mins: Verify Runtime + DB Init
- Check logs for successful startup and schema initialization.
- Run:
  - `curl http://127.0.0.1:8080/health`
- If failure:
  - capture exact trace
  - correct DSN/user/password/pooler host/port

### 40-60 mins: Provision Auth Client
- Execute:
  - `docker exec -it knowledge-gateway python scripts/provision_client.py --client-code <10-digit> --label codex`
- Securely store generated API key.
- Validate that `api_clients` is seeded and key works for `/mcp` requests.

### 60-90 mins: Cloudflare Tunnel Routing
- Add `mcp.<your-domain>` ingress to existing cloudflared config:
  - route to `http://localhost:8080`
- Restart cloudflared.
- Validate hostname routing from outside.

### 90-120 mins: Access Hardening + Smoke Tests
- Cloudflare Access app for MCP hostname.
- Keep app-level key auth enabled.
- Run smoke checks:
  - `create_employer`
  - `create_project`
  - `log_coding_session`
  - verify note created under `Employers/<Employer>/<Project>/<YYYY-MM-DD-update-...>/...`

---

## Critical Config Rules
- `DATABASE_URL` must be a Postgres DSN (not `https://...supabase.co`).
- Use Supabase Pooler endpoint (typically `:6543`) to avoid IPv6 direct-host issue.
- Supabase SSL enforcement requires `sslmode=require`.
- Use strong `API_KEY_PEPPER` (32+ random chars).

---

## Command Checklist
```bash
# Recreate container
docker rm -f knowledge-gateway || true

docker run -d --name knowledge-gateway \
  --restart unless-stopped \
  --user 1000:1000 \
  -p 127.0.0.1:8080:8080 \
  --env-file /opt/knowledge-gateway/.env \
  -v /opt/obsidian/vault:/data/vault \
  ghcr.io/singhamal001/knowledge-gateway:v0.1.0

# Verify
docker logs -f knowledge-gateway
curl http://127.0.0.1:8080/health

# Provision API client
docker exec -it knowledge-gateway python scripts/provision_client.py --client-code 1234567890 --label codex
```

---

## Stretch Goal (If time remains)
- Move to `docker-compose.yml` for repeatable deploy + restart policy + cloudflared sidecar.
