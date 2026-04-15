# GHCR Rebuild, Push, Pull, Deploy

## Scope
Release `knowledge-gateway` image from local machine to GHCR, then pull and run it on VPS.

## Image Coordinates
- Registry: `ghcr.io`
- Owner: `singhamal001`
- Image: `knowledge-gateway`
- Full image: `ghcr.io/singhamal001/knowledge-gateway`

## A) Local Build + Push (PowerShell)
From repo root (`knowledge-gateway`):

```powershell
$OWNER="singhamal001"
$IMAGE="knowledge-gateway"
$TAG="v0.1.3"
$FULL="ghcr.io/$OWNER/$IMAGE"

docker login ghcr.io -u $OWNER
docker build -t "${FULL}:${TAG}" .
docker push "${FULL}:${TAG}"

# Optional: also move latest tag
docker tag "${FULL}:${TAG}" "${FULL}:latest"
docker push "${FULL}:latest"
```

### Verify Published Tag
```powershell
docker pull "${FULL}:${TAG}"
docker images | Select-String "$OWNER/$IMAGE"
```

## B) VPS Pull + Restart Container
SSH into VPS and run:

```bash
OWNER="singhamal001"
IMAGE="knowledge-gateway"
TAG="v0.1.3"
FULL="ghcr.io/$OWNER/$IMAGE"

# Login if needed (PAT must include read:packages)
echo '<GHCR_PAT_WITH_read:packages>' | docker login ghcr.io -u "$OWNER" --password-stdin

# Pull image
docker pull "${FULL}:${TAG}"

# Stop/remove current container
docker rm -f knowledge-gateway 2>/dev/null || true

# Start new container
docker run -d --name knowledge-gateway \
  --restart unless-stopped \
  --user 1000:1000 \
  -p 127.0.0.1:8080:8080 \
  --env-file /opt/knowledge-gateway/.env \
  -v /opt/obsidian/vault:/data/vault \
  "${FULL}:${TAG}"
```

## C) Post-Deploy Checks (VPS)
```bash
docker inspect knowledge-gateway --format '{{.Config.Image}}'
docker logs --tail 80 knowledge-gateway
curl -i http://127.0.0.1:8080/health
```

Expected:
- image points to the new tag
- app startup logs show no exception
- `/health` returns `{"status":"ok"}`

## D) External MCP Check Through Cloudflare
```bash
curl --http1.1 -sS -i -X POST "https://mcp.amaxing.site/mcp" \
  -H "CF-Access-Client-Id: <CF_ID>" \
  -H "CF-Access-Client-Secret: <CF_SECRET>" \
  -H "Authorization: Bearer <KG_API_KEY>" \
  -H "X-Client-Code: <KG_CLIENT_CODE>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":"init-1","method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"deploy-check","version":"1.0"}}}'
```

## E) Rollback (If Needed)
```bash
PREV_TAG="v0.1.2"
FULL="ghcr.io/singhamal001/knowledge-gateway"

docker rm -f knowledge-gateway 2>/dev/null || true
docker run -d --name knowledge-gateway \
  --restart unless-stopped \
  --user 1000:1000 \
  -p 127.0.0.1:8080:8080 \
  --env-file /opt/knowledge-gateway/.env \
  -v /opt/obsidian/vault:/data/vault \
  "${FULL}:${PREV_TAG}"
```

## Notes
- Keep `.env` only on VPS; do not bake secrets into image.
- Tag every release (`v0.1.x`) so rollback is instant.
- Prefer testing image locally before push.

