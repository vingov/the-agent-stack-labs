"""Harmless stdio server for the optional Part 5 MCP experiment."""
import os
from mcp.server import MCPServer

server = MCPServer("part5-synthetic")


@server.tool()
def environment_report() -> dict:
    """Report presence of two synthetic variables, never their values."""
    return {
        "ambient_canary_present": "PART5_AMBIENT_CANARY" in os.environ,
        "explicit_canary_present": "PART5_EXPLICIT_CANARY" in os.environ,
    }


@server.tool()
def withheld_noop() -> str:
    """A harmless second tool used to check Hermes tool selection."""
    return "synthetic-noop"


if __name__ == "__main__":
    server.run(transport="stdio")
