import importlib
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest


REQUIRED_ENV: Dict[str, str] = {
    "SCALEKIT_ENVIRONMENT_URL": "https://example.scalekit.local",
    "SCALEKIT_CLIENT_ID": "client-id",
    "SCALEKIT_CLIENT_SECRET": "client-secret",
    "SCALEKIT_RESOURCE_METADATA_URL": "https://example.scalekit.local/.well-known/oauth-protected-resource/mcp",
    "SCALEKIT_AUDIENCE_NAME": "https://example.scalekit.local/mcp/",
    "METADATA_JSON_RESPONSE": json.dumps(
        {
            "authorization_servers": ["https://example.scalekit.local/resources/client-id"],
            "bearer_methods_supported": ["header"],
            "resource": "https://example.scalekit.local/mcp/",
            "resource_documentation": "https://example.scalekit.local/mcp/docs",
            "scopes_supported": ["search:read"],
        }
    ),
}


@contextmanager
def patched_environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Ensure required environment variables are present for settings import."""

    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    # Reload configuration-driven modules so they pick up patched env vars
    for module_name in ["src.config", "src.auth", "src.mcp", "src.server"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            __import__(module_name)

    try:
        yield
    finally:
        # Modules will be reloaded for each test via the context manager, so no cleanup needed
        pass


def test_healthcheck_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    with patched_environment(monkeypatch):
        from fastapi.testclient import TestClient
        from src.server import app

        with TestClient(app) as client:
            response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "payment-mcp"}


def test_initialize_request_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    with patched_environment(monkeypatch):
        from fastapi.testclient import TestClient
        from src.server import app

        handshake_payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "pytest", "version": "1.0"},
                "capabilities": {},
            },
        }

        scalekit_mock = Mock()
        scalekit_mock.validate_token.return_value = None

        with patch("src.auth.get_scalekit_client", return_value=scalekit_mock):
            with TestClient(app) as client:
                response = client.post(
                    "/mcp",
                    json=handshake_payload,
                    headers={"Authorization": "Bearer fake-token"},
                )

        assert response.status_code == 200
        body = response.json()
        assert body.get("jsonrpc") == "2.0"
        assert body.get("id") == 1
        assert "result" in body
