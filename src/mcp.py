from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse


async def _healthcheck(_: Request) -> JSONResponse:
    """Basic healthcheck for direct MCP app access."""

    return JSONResponse({"status": "ok", "service": "payment-mcp"})

# Create an MCP server
mcp = FastMCP("payment-mcp")


def create_streamable_http_app() -> Starlette:
    """Return the ASGI application used to serve the MCP protocol."""

    app = mcp.streamable_http_app()

    app.router.add_route("/", _healthcheck, methods=["GET"])

    return app


# Add a tool that uses Tavily
@mcp.tool()
def web_search(query: str) -> str:
    """
    Use this tool to search the web for information.

    Args:
        query: The search query.

    Returns:
        The search results.
    """
    try:

        return "ankit"
    except Exception as e:
        return {"error": str(e)}
