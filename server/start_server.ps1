#!/usr/bin/env pwsh
# Neuber Correction Server Start Script (Windows PowerShell)
# Usage: .\start_server.ps1 [PORT]

param(
    [int]$Port = 8000
)

# Set error action preference to continue silently
$ErrorActionPreference = "SilentlyContinue"

# Function to check if port is available
function Test-Port {
    param([int]$Port)
    try {
        $connection = New-Object System.Net.Sockets.TcpClient
        $connection.Connect("localhost", $Port)
        $connection.Close()
        return $false  # Port is in use
    }
    catch {
        return $true   # Port is available
    }
}

# Function to find available port
function Find-AvailablePort {
    param([int]$StartPort = 8000)
    
    $port = $StartPort
    while (-not (Test-Port -Port $port)) {
        $port++
        if ($port -gt 65535) {
            Write-Error "No available ports found"
            exit 1
        }
    }
    return $port
}

# Check if uv is available
if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Error "uv is not installed or not in PATH. Please install uv first."
    exit 1
}

# Check if dependencies are installed
if (-not (Test-Path "uv.lock")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    uv sync
}

# Find available port if specified port is in use
$actualPort = Find-AvailablePort -StartPort $Port

if ($actualPort -ne $Port) {
    Write-Host "Port $Port is in use, using port $actualPort instead" -ForegroundColor Yellow
}

# Set environment variables for silent operation
$env:PYTHONUNBUFFERED = "1"
$env:UV_SILENT = "1"

# Start the server silently
Write-Host "Starting Neuber Correction Server on port $actualPort..." -ForegroundColor Green
Write-Host "Server URL: http://localhost:$actualPort" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray

try {
    # Start uvicorn with minimal output
    uv run uvicorn app.main:app --host 0.0.0.0 --port $actualPort --no-access-log --log-level error
}
catch {
    Write-Error "Failed to start server: $_"
    exit 1
} 