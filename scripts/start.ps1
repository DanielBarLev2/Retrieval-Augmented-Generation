# Retrieval-Augmented-Generation Startup Script
# This script starts all necessary services for the RAG application

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RAG Application Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker status..." -ForegroundColor Yellow
try {
    $dockerStatus = docker ps 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker is running!" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Docker is not installed or not running." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Start Docker containers
Write-Host "Starting Docker containers..." -ForegroundColor Yellow

# Check if Qdrant container exists
$qdrantExists = docker ps -a --filter "name=qdrant-rag" --format "{{.Names}}" 2>$null
if ($qdrantExists -eq "qdrant-rag") {
    Write-Host "Qdrant container already exists. Starting it..." -ForegroundColor Cyan
    docker start qdrant-rag
} else {
    Write-Host "Creating and starting Qdrant container..." -ForegroundColor Cyan
    docker run -d --name qdrant-rag -p 6333:6333 qdrant/qdrant:latest
}

# Check if MongoDB container exists
$mongoExists = docker ps -a --filter "name=mongo-rag" --format "{{.Names}}" 2>$null
if ($mongoExists -eq "mongo-rag") {
    Write-Host "MongoDB container already exists. Starting it..." -ForegroundColor Cyan
    docker start mongo-rag
} else {
    Write-Host "Creating and starting MongoDB container..." -ForegroundColor Cyan
    docker run -d --name mongo-rag -p 27017:27017 mongo:7
}

Write-Host "Docker containers started successfully!" -ForegroundColor Green
Write-Host ""

# Wait for services to be ready
Write-Host "Waiting for services to initialize (5 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Start Backend Server
Write-Host "Starting Backend Server..." -ForegroundColor Yellow
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $projectRoot "backend"
$backendEnvName = "RAG"
$condaCommand = Get-Command "conda.exe" -ErrorAction SilentlyContinue
if ($null -ne $condaCommand) {
    $condaExecutable = $condaCommand.Source
} else {
    $condaExecutable = $null
}

if ($null -ne $condaExecutable) {
    Write-Host "Launching backend with Conda environment '$backendEnvName'..." -ForegroundColor Cyan
    $backendCommand = [string]::Format(
        "cd '{0}'; Write-Host ""Starting FastAPI Backend in Conda environment '{1}'..."" -ForegroundColor Cyan; & ""{2}"" run --no-capture-output -n ""{1}"" uvicorn app.main:app --reload",
        $backendPath,
        $backendEnvName,
        $condaExecutable
    )
} else {
    Write-Host "WARNING: 'conda.exe' not found on PATH. Starting backend in current environment." -ForegroundColor Yellow
    $backendCommand = [string]::Format(
        "cd '{0}'; Write-Host ""Starting FastAPI Backend in current environment (conda.exe not found)."" -ForegroundColor Yellow; uvicorn app.main:app --reload",
        $backendPath
    )
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand
Write-Host "Backend server starting in new window..." -ForegroundColor Green
Write-Host ""

# Wait a moment before starting frontend
Start-Sleep -Seconds 2

# Start Frontend Server
Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
$frontendPath = Join-Path $projectRoot "web"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; Write-Host 'Starting React Frontend...' -ForegroundColor Cyan; npm run dev"
Write-Host "Frontend server starting in new window..." -ForegroundColor Green
Write-Host ""

# Display information
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services:" -ForegroundColor Yellow
Write-Host "  - Qdrant Vector DB:  http://localhost:6333" -ForegroundColor White
Write-Host "  - MongoDB:           mongodb://localhost:27017" -ForegroundColor White
Write-Host "  - Backend API:       http://localhost:8000" -ForegroundColor White
Write-Host "  - Backend Docs:      http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Frontend:          http://localhost:5173 (check terminal for exact port)" -ForegroundColor White
Write-Host ""
Write-Host "Note: Backend and Frontend are running in separate PowerShell windows." -ForegroundColor Cyan
Write-Host "Close those windows to stop the servers." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

