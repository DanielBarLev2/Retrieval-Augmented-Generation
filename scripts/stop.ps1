# Retrieval-Augmented-Generation Shutdown Script
# This script stops all RAG application services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RAG Application Shutdown Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop Backend and Frontend processes
Write-Host "Stopping Backend and Frontend servers..." -ForegroundColor Yellow
try {
    # Stop uvicorn processes
    Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
    # Stop node processes (Vite dev server)
    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowTitle -match "vite"} | Stop-Process -Force
    Write-Host "Server processes stopped." -ForegroundColor Green
} catch {
    Write-Host "No server processes found or already stopped." -ForegroundColor Yellow
}
Write-Host ""

# Stop Docker containers
Write-Host "Stopping Docker containers..." -ForegroundColor Yellow

$qdrantRunning = docker ps --filter "name=qdrant-rag" --format "{{.Names}}" 2>$null
if ($qdrantRunning -eq "qdrant-rag") {
    Write-Host "Stopping Qdrant container..." -ForegroundColor Cyan
    docker stop qdrant-rag
} else {
    Write-Host "Qdrant container is not running." -ForegroundColor Yellow
}

$mongoRunning = docker ps --filter "name=mongo-rag" --format "{{.Names}}" 2>$null
if ($mongoRunning -eq "mongo-rag") {
    Write-Host "Stopping MongoDB container..." -ForegroundColor Cyan
    docker stop mongo-rag
} else {
    Write-Host "MongoDB container is not running." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All Services Stopped!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: Docker containers are stopped but not removed." -ForegroundColor Cyan
Write-Host "They will be reused on next startup." -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

