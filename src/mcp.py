from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("payment-mcp")


def create_streamable_http_app() -> FastAPI:
    """Return the FastAPI application used to serve the MCP protocol."""

    app = mcp.streamable_http_app()

    @app.get("/")
    async def healthcheck() -> dict[str, str]:
        """Basic healthcheck for direct MCP app access."""

        return {"status": "ok", "service": "payment-mcp"}

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
