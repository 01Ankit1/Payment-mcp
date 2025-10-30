from mcp.server.fastmcp import FastMCP
from typing import Dict, List

from .config import settings

# Create an MCP server
mcp = FastMCP("payment-mcp")


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
