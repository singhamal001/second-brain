# Update Log - 2026-04-08

## Session Summary
This log captures the implementation and VPS deployment progress for the `knowledge-gateway` service (MCP + FastAPI + Supabase + Obsidian vault integration), including key technical decisions, mistakes, and corrections.

## What Was Implemented
- Built `knowledge-gateway` Python service with:
  - FastAPI app + MCP endpoint (`/mcp`)
  - Auth middleware (Bearer API key + optional `X-Client-Code`)
  - Dynamic table management with non-destructive model (archive-only, no hard delete/drop)
  - Dual-write logging flows (Supabase/Postgres + Obsidian markdown)
  - Audit logging (`activity_log`)
- Implemented Obsidian folder strategy requested by user:
  - `Employers/<Employer>/<Project>/<YYYY-MM-DD-update-<feature>>/<note>.md`
  - Auto-create employer/project folders on `create_project`
- Added Docker artifacts:
  - `Dockerfile`
  - `.dockerignore`
- Built image locally and pushed/pulled via GHCR.

## Deployment Process Followed
1. Created/pushed container image from local machine to GHCR.
2. Logged into GHCR on VPS and successfully pulled image:
   - `ghcr.io/singhamal001/knowledge-gateway:v0.1.0`
3. Prepared runtime env file on VPS (`/opt/knowledge-gateway/.env`).
4. Mounted existing host Obsidian vault into container (instead of creating a new vault path):
   - host: `/opt/obsidian/vault`
   - container: `/data/vault`
5. Set app vault root to isolated subfolder for AI writes:
   - `VAULT_ROOT=/data/vault/knowledge-gateway`

## Key Confusions and Technical Clarifications

### 1) Supabase project URL vs Postgres connection string
- Confusion: used `https://<project-ref>.supabase.co` as `DATABASE_URL`.
- Clarification: this is the Supabase API/project URL, not the Postgres DSN.
- Required format for app DB connection:
  - `postgresql://...`

### 2) Direct DB host + IPv6 routing issue
- Attempted DSN with direct host:
  - `db.<project-ref>.supabase.co:5432`
- Runtime failure in container:
  - `Network is unreachable`
  - DB resolution attempted IPv6 address.
- Resolution direction:
  - Use Supabase **Pooler** connection string (typically port `6543`) from dashboard.

### 3) SSL-only DB connections enabled
- User enabled "Enforce SSL on incoming connections" in Supabase.
- Requirement:
  - Ensure `?sslmode=require` is present in `DATABASE_URL`.
- Without SSL mode, connection may fail or be rejected by policy.

### 4) Secrets and URL-encoding details
- If DB password contains reserved URL characters (e.g. `@`), encode them (e.g. `@` -> `%40`).
- `API_KEY_PEPPER` should be long random secret (32+ chars), not a short/simple string.

## Current Status
- Container image pull from GHCR: successful.
- Container startup with current DSN: failed due DB connectivity (IPv6 route issue on direct host).
- Next action: switch `.env` `DATABASE_URL` to Supabase Pooler DSN with SSL required.

## Next-Session Checklist
1. Update `/opt/knowledge-gateway/.env` with Pooler DSN (`postgresql://...pooler...:6543/postgres?sslmode=require`).
2. Recreate container:
   - `docker rm -f knowledge-gateway`
   - rerun `docker run ...`
3. Verify:
   - `docker logs -f knowledge-gateway`
   - `curl http://127.0.0.1:8080/health`
4. Provision API client key:
   - `docker exec -it knowledge-gateway python scripts/provision_client.py --client-code <10-digit> --label codex`
5. Add MCP hostname through existing Cloudflare Tunnel + Access policy.

## Notes on Existing Vault + Git Backup
- Existing Obsidian setup is already Git-backed with cron.
- Any notes written by `knowledge-gateway` under `/opt/obsidian/vault/knowledge-gateway` will be naturally included in that backup flow.
