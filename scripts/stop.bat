@echo off
REM Retrieval-Augmented-Generation Shutdown Script
REM This script stops all RAG application services

echo ========================================
echo   RAG Application Shutdown Script
echo ========================================
echo.

REM Stop Backend and Frontend processes
echo Stopping Backend and Frontend servers...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq RAG Backend Server*" 2>nul
taskkill /F /IM node.exe /FI "WINDOWTITLE eq RAG Frontend Server*" 2>nul
echo Server processes stopped.
echo.

REM Stop Docker containers
echo Stopping Docker containers...

docker ps --filter "name=qdrant-rag" --format "{{.Names}}" | findstr "qdrant-rag" >nul 2>&1
if not errorlevel 1 (
    echo Stopping Qdrant container...
    docker stop qdrant-rag
) else (
    echo Qdrant container is not running.
)

docker ps --filter "name=mongo-rag" --format "{{.Names}}" | findstr "mongo-rag" >nul 2>&1
if not errorlevel 1 (
    echo Stopping MongoDB container...
    docker stop mongo-rag
) else (
    echo MongoDB container is not running.
)

echo.
echo ========================================
echo   All Services Stopped!
echo ========================================
echo.
echo Note: Docker containers are stopped but not removed.
echo They will be reused on next startup.
echo.
pause

