import json
import os
from typing import Any, Dict, List

try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback when package missing
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False

load_dotenv()


class Settings:
    """Application settings sourced from environment variables."""

    SCALEKIT_ENVIRONMENT_URL: str
    SCALEKIT_CLIENT_ID: str
    SCALEKIT_CLIENT_SECRET: str
    SCALEKIT_RESOURCE_METADATA_URL: str
    SCALEKIT_AUDIENCE_NAME: str
    METADATA_JSON_RESPONSE: str
    MCP_TOOL_SCOPE: str
    PORT: int

    def __init__(self) -> None:
        self.SCALEKIT_ENVIRONMENT_URL = os.environ.get("SCALEKIT_ENVIRONMENT_URL", "").strip()
        self.SCALEKIT_CLIENT_ID = os.environ.get("SCALEKIT_CLIENT_ID", "").strip()
        self.SCALEKIT_CLIENT_SECRET = os.environ.get("SCALEKIT_CLIENT_SECRET", "").strip()
        self.SCALEKIT_RESOURCE_METADATA_URL = os.environ.get("SCALEKIT_RESOURCE_METADATA_URL", "").strip()
        self.SCALEKIT_AUDIENCE_NAME = os.environ.get("SCALEKIT_AUDIENCE_NAME", "").strip()
        self.METADATA_JSON_RESPONSE = os.environ.get("METADATA_JSON_RESPONSE", "{}").strip()
        self.MCP_TOOL_SCOPE = os.environ.get("MCP_TOOL_SCOPE", "").strip()
        self.PORT = int(os.environ.get("PORT", 8080))

        self._validate_required_settings()

    def _validate_required_settings(self) -> None:
        required = {
            "SCALEKIT_ENVIRONMENT_URL": self.SCALEKIT_ENVIRONMENT_URL,
            "SCALEKIT_CLIENT_ID": self.SCALEKIT_CLIENT_ID,
            "SCALEKIT_CLIENT_SECRET": self.SCALEKIT_CLIENT_SECRET,
            "SCALEKIT_RESOURCE_METADATA_URL": self.SCALEKIT_RESOURCE_METADATA_URL,
            "SCALEKIT_AUDIENCE_NAME": self.SCALEKIT_AUDIENCE_NAME,
        }

        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(sorted(missing))
            )

    def metadata_response(self) -> Dict[str, Any]:
        try:
            return json.loads(self.METADATA_JSON_RESPONSE or "{}")
        except json.JSONDecodeError as exc:  # pragma: no cover - guarded in runtime path
            raise ValueError(f"Invalid METADATA_JSON_RESPONSE JSON: {exc}") from exc

    def tool_scopes(self) -> List[str]:
        if not self.MCP_TOOL_SCOPE:
            return []
        return [scope.strip() for scope in self.MCP_TOOL_SCOPE.split(",") if scope.strip()]


settings = Settings()
