import os
import json
import asyncio


from langchain_mcp_adapters.client import MultiServerMCPClient
from ..logging.logger import logger

async def load_mcp_servers_async(config_path):
    """
    Load MCP server definitions from a JSON config file.
    Expects a top-level 'mcpServers' dict in the config.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Read config file in a separate thread to avoid blocking
    def read_config():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    config = await asyncio.to_thread(read_config)

    servers = config.get("mcpServers", {})
    logger.info("starting MCP servers")
    

    # Add default transports if missing
    for name, server in servers.items():
        if "command" in server and "transport" not in server:
            server["transport"] = "stdio"
        if "url" in server and "transport" not in server:
            server["transport"] = "streamable_http"

    return servers


mcp_config_path = "src/MCP/MCP.json"
mcp_servers = None

_client = None

async def get_mcp_client():
    global _client, mcp_servers
    
    if _client is None:
        if mcp_servers is None:
            mcp_servers = await load_mcp_servers_async(str(mcp_config_path))
            print(mcp_servers)
            print("MCP Servers loaded successfully.")
        
        _client = MultiServerMCPClient(mcp_servers)
    return _client

async def main():
    client = await get_mcp_client()
    all_mcp_tools = await client.get_tools()
    logger.info(f"Total tools available from MCP servers: {len(all_mcp_tools)}")
    print(len(all_mcp_tools)) 
    return all_mcp_tools

all_mcp_tools = asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
