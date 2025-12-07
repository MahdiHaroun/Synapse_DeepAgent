#!/bin/bash

# MCP Servers Startup Script
# Runs all FastAPI MCP servers simultaneously

echo "🔥 Starting All MCP Servers"
echo "=================================================="

# Function to handle Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Shutting down all MCP servers..."
    jobs -p | xargs -r kill
    wait
    echo "✅ All servers stopped"
    exit 0
}

# Set up signal handler
trap cleanup SIGINT SIGTERM

# Check if we're in the project root
if [[ ! -f "pyproject.toml" || ! -d "src" || ! -d "Backend" ]]; then
    echo "❌ Please run this script from the project root directory"
    echo "Current directory: $(pwd)"
    echo "Expected files/directories: pyproject.toml, src/, Backend/"
    exit 1
fi

# Activate virtual environment if it exists
if [[ -f ".venv/bin/activate" ]]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ No Python interpreter found"
    exit 1
fi

echo "Using Python: $(which $PYTHON_CMD)"

# Start all servers in background
echo "🚀 Starting Google Gmail Server..."
$PYTHON_CMD -m Backend.mcp.google_gmail.server &

echo "🚀 Starting AWS S3 Server..."
$PYTHON_CMD -m Backend.mcp.aws_S3_server.server &

echo "🚀 Starting Google Calendar Server..."
$PYTHON_CMD -m Backend.mcp.google_calender.server &

echo "🚀 Starting Analysis Tools Server..."
$PYTHON_CMD -m Backend.mcp.analysis_tools_server.server &

echo "🚀 Starting Auth Server..."
$PYTHON_CMD -m Backend.mcp.auth_server.server &

echo "Starting Web Search Server..."
$PYTHON_CMD -m Backend.mcp.web_server.server &
echo "🚀 Starting RAG Service Server..."
$PYTHON_CMD -m Backend.mcp.rag_server.server &

echo ""
echo "✅ All servers started!"
echo "📝 Server endpoints:"
echo "   - Gmail MCP: http://localhost:3050"
echo "   - AWS S3 MCP: http://localhost:3000" 
echo "   - Calendar MCP: http://localhost:3030"
echo "   - Analysis MCP: http://localhost:3040"
echo "   - Auth MCP: http://localhost:3060"
echo "   - Web Search MCP: http://localhost:3020"
echo "   - RAG Service MCP: http://localhost:3010"
echo ""
echo "Press Ctrl+C to stop all servers"

# Wait for all background jobs
wait