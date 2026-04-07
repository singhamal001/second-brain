from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Settings, get_settings
from .context import RequestAuthContext, current_auth_context
from .mcp_server import create_mcp_server
from .services.audit import AuditService
from .services.auth import AuthService
from .services.db_store import DBStore
from .services.errors import AuthError
from .services.obsidian_store import ObsidianStore
from .services.reporting import ReportingService
from .services.schema_manager import SchemaManager

logger = logging.getLogger(__name__)


def _extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[len("Bearer ") :].strip()


def _cf_bypass_allowed(settings: Settings, request: Request) -> bool:
    if not settings.allow_cf_bypass_for_local:
        return False
    host = (request.client.host if request.client else "") or ""
    return host in {"127.0.0.1", "localhost", "testclient"}


def create_app() -> FastAPI:
    settings = get_settings()

    db_store = DBStore(settings.database_url, app_schema=settings.app_schema)
    db_store.initialize()

    auth_service = AuthService(db_store=db_store, api_key_pepper=settings.api_key_pepper)
    obsidian_store = ObsidianStore(settings.vault_root)
    schema_manager = SchemaManager(db_store)
    reporting_service = ReportingService(db_store)
    audit_service = AuditService(db_store)

    mcp = create_mcp_server(
        name=settings.mcp_server_name,
        version=settings.mcp_server_version,
        db_store=db_store,
        obsidian_store=obsidian_store,
        schema_manager=schema_manager,
        reporting_service=reporting_service,
        audit_service=audit_service,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("knowledge gateway started")
        yield
        logger.info("knowledge gateway stopped")

    app = FastAPI(title="knowledge-gateway", version=settings.mcp_server_version, lifespan=lifespan)

    app.state.settings = settings
    app.state.db_store = db_store
    app.state.auth_service = auth_service
    app.state.mcp = mcp

    @app.middleware("http")
    async def mcp_auth_middleware(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/mcp"):
            return await call_next(request)

        if settings.require_cloudflare_access and not _cf_bypass_allowed(settings, request):
            if not request.headers.get("Cf-Access-Jwt-Assertion") and not request.headers.get(
                "CF-Access-Authenticated-User-Email"
            ):
                return JSONResponse(status_code=403, content={"detail": "cloudflare access validation failed"})

        api_key = _extract_bearer_token(request)
        client_code = request.headers.get("X-Client-Code")
        try:
            auth_result = auth_service.verify(api_key=api_key, client_code=client_code)
        except AuthError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})

        token = current_auth_context.set(
            RequestAuthContext(
                client_id=auth_result.client_id,
                client_code=auth_result.client_code,
                label=auth_result.label,
            )
        )
        try:
            return await call_next(request)
        finally:
            current_auth_context.reset(token)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/mcp", mcp.streamable_http_app())
    return app
