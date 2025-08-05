#!/bin/bash
# Neuber Correction Server Start Script (Unix/Linux)
# Usage: ./start_server.sh [PORT]

set -e

# Default port
PORT=${1:-8000}

# Function to check if port is available
check_port() {
    local port=$1
    if command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":$port "
    elif command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":$port "
    elif command -v lsof >/dev/null 2>&1; then
        lsof -i :$port >/dev/null 2>&1
    else
        # Fallback: try to connect to the port
        timeout 1 bash -c "</dev/tcp/localhost/$port" 2>/dev/null || return 0
    fi
    return $?
}

# Function to find available port
find_available_port() {
    local start_port=$1
    local port=$start_port
    
    while check_port $port; do
        port=$((port + 1))
        if [ $port -gt 65535 ]; then
            echo "No available ports found" >&2
            exit 1
        fi
    done
    echo $port
}

# Check if uv is available and find its path
UV_PATH=""
if command -v uv >/dev/null 2>&1; then
    UV_PATH=$(command -v uv)
elif [ -f "/home/ramsaier/.local/bin/uv" ]; then
    UV_PATH="/home/ramsaier/.local/bin/uv"
elif [ -f "/home/ramsaier/.cargo/bin/uv" ]; then
    UV_PATH="/home/ramsaier/.cargo/bin/uv"
elif [ -f "/usr/local/bin/uv" ]; then
    UV_PATH="/usr/local/bin/uv"
elif [ -f "/usr/bin/uv" ]; then
    UV_PATH="/usr/bin/uv"
else
    echo "Error: uv is not installed or not found in common locations." >&2
    echo "Please install uv or ensure it's in PATH." >&2
    exit 1
fi

# Check if dependencies are installed
if [ ! -f "uv.lock" ]; then
    echo "Installing dependencies..."
    $UV_PATH sync >/dev/null 2>&1
fi

# Find available port if specified port is in use
actual_port=$(find_available_port $PORT)

if [ "$actual_port" != "$PORT" ]; then
    echo "Port $PORT is in use, using port $actual_port instead"
fi

# Set environment variables for silent operation
export PYTHONUNBUFFERED=1
export UV_SILENT=1

# Start the server silently
echo "Starting Neuber Correction Server on port $actual_port..."
echo "Server URL: http://localhost:$actual_port"
echo "Press Ctrl+C to stop the server"

# Start uvicorn with minimal output
uv run uvicorn app.main:app --host 0.0.0.0 --port $actual_port --no-access-log --log-level error 