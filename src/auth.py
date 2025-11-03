import json
import logging
from typing import Any, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from scalekit import ScalekitClient
from scalekit.common.scalekit import TokenValidationOptions
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

logger = logging.getLogger(__name__)


_scalekit_client: ScalekitClient | None = None


def get_scalekit_client() -> ScalekitClient:
    global _scalekit_client
    if _scalekit_client is None:
        _scalekit_client = ScalekitClient(
            settings.SCALEKIT_ENVIRONMENT_URL,
            settings.SCALEKIT_CLIENT_ID,
            settings.SCALEKIT_CLIENT_SECRET,
        )
    return _scalekit_client


class AuthMiddleware(BaseHTTPMiddleware):
    """OAuth Bearer token enforcement for MCP HTTP requests."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/.well-known"):
            return await call_next(request)
        if request.method == "GET":
            return await call_next(request)
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        token = self._extract_bearer_token(request)
        if token is None:
            return self._unauthorized("Missing or invalid authorization header")

        body_bytes = await request.body()
        payload = self._parse_json(body_bytes)

        options = TokenValidationOptions(
            issuer=settings.SCALEKIT_ENVIRONMENT_URL,
            audience=[settings.SCALEKIT_AUDIENCE_NAME],
        )

        if payload.get("method") == "tools/call":
            scopes = settings.tool_scopes()
            if scopes:
                options.required_scopes = scopes

        try:
            get_scalekit_client().validate_token(token, options=options)
        except Exception as exc:  # pragma: no cover - requires external service
            logger.warning("Token validation failed: %s", exc)
            return self._unauthorized("Token validation failed")

        async def receive() -> Dict[str, Any]:
            if receive.sent:
                return {"type": "http.request", "body": b"", "more_body": False}
            receive.sent = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        receive.sent = False  # type: ignore[attr-defined]

        new_request = Request(request.scope, receive)  # type: ignore[arg-type]
        response = await call_next(new_request)
        return response

    @staticmethod
    def _parse_json(body: bytes) -> Dict[str, Any]:
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _extract_bearer_token(request: Request) -> str | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header.split(" ", 1)[1].strip()

    @staticmethod
    def _unauthorized(detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "error_description": detail},
            headers={
                "WWW-Authenticate": "Bearer realm=\"OAuth\"",
            },
        )
