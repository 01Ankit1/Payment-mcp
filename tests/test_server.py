import importlib
import os
import sys
import unittest
from contextlib import contextmanager
from typing import Dict
from unittest.mock import Mock, patch

REQUIRED_ENV: Dict[str, str] = {
    "SCALEKIT_ENVIRONMENT_URL": "https://example.scalekit.local",
    "SCALEKIT_CLIENT_ID": "client-id",
    "SCALEKIT_CLIENT_SECRET": "client-secret",
    "SCALEKIT_RESOURCE_METADATA_URL": "https://example.scalekit.local/.well-known/oauth-protected-resource/mcp",
    "SCALEKIT_AUDIENCE_NAME": "https://example.scalekit.local/mcp/",
    "METADATA_JSON_RESPONSE": "{\"authorization_servers\":[\"https://example.scalekit.local/resources/client-id\"],\"bearer_methods_supported\":[\"header\"],\"resource\":\"https://example.scalekit.local/mcp/\",\"resource_documentation\":\"https://example.scalekit.local/mcp/docs\",\"scopes_supported\":[\"search:read\"]}",
    "MCP_TOOL_SCOPE": "search:read",
}


@contextmanager
def patched_environment():
    previous = {key: os.environ.get(key) for key in REQUIRED_ENV}
    os.environ.update(REQUIRED_ENV)

    for module_name in ["src.config", "src.auth", "src.mcp", "src.server"]:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            __import__(module_name)

    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class ServerTestCase(unittest.TestCase):
    def test_healthcheck_endpoint(self):
        with patched_environment():
            from fastapi.testclient import TestClient
            from src.server import app

            with TestClient(app) as client:
                response = client.get("/")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "service": "payment-mcp"})

    def test_initialize_request_succeeds(self):
        with patched_environment():
            from fastapi.testclient import TestClient
            from src.server import app

            handshake_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "unittest", "version": "1.0"},
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

            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body.get("jsonrpc"), "2.0")
            self.assertEqual(body.get("id"), 1)
            self.assertIn("result", body)


if __name__ == "__main__":
    unittest.main()
