import sys
from pathlib import Path

# Ensure project root is in Python path for absolute imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import contextlib
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth import AuthMiddleware
from src.config import settings
import json
from src.mcp import mcp as mcp

# Create a combined lifespan to manage the MCP session manager
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# MCP well-known endpoint
@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_metadata():
    """
    OAuth 2.0 Protected Resource Metadata endpoint for MCP client discovery.
    Required by the MCP specification for authorization server discovery.
    """

    response = json.loads(settings.METADATA_JSON_RESPONSE)
    return response

# Create and mount the MCP server with authentication
app.add_middleware(AuthMiddleware)
app.mount("/", mcp)

def main():
    """Main entry point for the MCP server."""
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT, log_level="debug")

if __name__ == "__main__":
    main()
