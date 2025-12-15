#!/bin/bash

# Entrypoint script for Docker container
# Starts MCP servers in background and then starts the main FastAPI application

set -e

echo "🚀 Starting Synapse DeepAgent"
echo "=================================================="

# Start MCP servers in background
echo "📡 Starting MCP Servers..."

python -m Backend.mcp.google_gmail.server &
echo "   ✓ Gmail MCP (port 3050)"

python -m Backend.mcp.aws_S3_server.server &
echo "   ✓ AWS S3 MCP (port 3000)"

python -m Backend.mcp.google_calender.server &
echo "   ✓ Calendar MCP (port 3030)"

python -m Backend.mcp.analysis_tools_server.server &
echo "   ✓ Analysis MCP (port 3040)"

python -m Backend.mcp.auth_server.server &
echo "   ✓ Auth MCP (port 3060)"

python -m Backend.mcp.web_server.server &
echo "   ✓ Web Search MCP (port 3020)"

python -m Backend.mcp.rag_server.server &
echo "   ✓ RAG Service MCP (port 3010)"

echo ""
echo "✅ All MCP servers started"

sleep 30
echo "🌐 Starting Main API on port 8070..."
echo ""

# Start the main application (this keeps the container running)
exec python -m Backend.api.main
