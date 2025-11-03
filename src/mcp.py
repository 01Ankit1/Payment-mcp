from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("payment-mcp")


def create_streamable_http_app() -> FastAPI:
    """Return the FastAPI application used to serve the MCP protocol."""

    app = mcp.streamable_http_app()

    @app.get("/")
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "payment-mcp"}

    return app


@mcp.tool()
def echo(message: str) -> str:
    """Return the provided message."""

    return message
