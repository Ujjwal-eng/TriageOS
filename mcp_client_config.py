"""
Central config for connecting to all three MCP servers, and a helper to
load their tools as LangChain-compatible tool objects.
"""
 
import asyncio
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient
 
SERVERS_DIR = Path(__file__).parent / "mcp_servers"
 
MCP_SERVERS = {
    "crm": {
        "command": "python",
        "args": [str(SERVERS_DIR / "crm_server.py")],
        "transport": "stdio",
    },
    "kb": {
        "command": "python",
        "args": [str(SERVERS_DIR / "kb_server.py")],
        "transport": "stdio",
    },
    "email": {
        "command": "python",
        "args": [str(SERVERS_DIR / "email_server.py")],
        "transport": "stdio",
    },
}
 
 
async def load_all_tools() -> dict:
    """Connects to all three servers, returns their tools grouped by server.
    e.g. {"crm": [get_invoice, issue_refund, ...],
          "kb": [search_kb],
          "email": [send_email]}
    Call this ONCE, when your app starts up — not per-request.
    """
    client = MultiServerMCPClient(MCP_SERVERS)
    tools_by_server = {}
    for server_name in MCP_SERVERS:
        tools_by_server[server_name] = await client.get_tools(server_name=server_name)
    return tools_by_server
 
 
if __name__ == "__main__":
    # Quick manual check: confirm all three servers start and list their tools.
    tools_by_server = asyncio.run(load_all_tools())
    for server, tools in tools_by_server.items():
        print(f"{server}: {[t.name for t in tools]}")
 
