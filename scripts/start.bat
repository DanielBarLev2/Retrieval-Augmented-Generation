@echo off
REM Retrieval-Augmented-Generation Startup Script (Batch File)
REM This script starts all necessary services for the RAG application

echo ========================================
echo   RAG Application Startup Script
echo ========================================
echo.

REM Check if Docker is running
echo Checking Docker status...
docker ps >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)
echo Docker is running!
echo.

REM Start Docker containers
echo Starting Docker containers...

REM Check and start Qdrant
docker ps -a --filter "name=qdrant-rag" --format "{{.Names}}" | findstr "qdrant-rag" >nul 2>&1
if errorlevel 1 (
    echo Creating and starting Qdrant container...
    docker run -d --name qdrant-rag -p 6333:6333 qdrant/qdrant:latest
) else (
    echo Starting Qdrant container...
    docker start qdrant-rag
)

REM Check and start MongoDB
docker ps -a --filter "name=mongo-rag" --format "{{.Names}}" | findstr "mongo-rag" >nul 2>&1
if errorlevel 1 (
    echo Creating and starting MongoDB container...
    docker run -d --name mongo-rag -p 27017:27017 mongo:7
) else (
    echo Starting MongoDB container...
    docker start mongo-rag
)

echo Docker containers started successfully!
echo.

REM Wait for services to be ready
echo Waiting for services to initialize...
timeout /t 5 /nobreak >nul
echo.

REM Get the project root directory (parent of scripts folder)
set "PROJECT_ROOT=%~dp0.."

REM Start Backend Server
echo Starting Backend Server...
start "RAG Backend Server" cmd /k "cd /d "%PROJECT_ROOT%\backend" && echo Starting FastAPI Backend... && uvicorn app.main:app --reload"
echo Backend server starting in new window...
echo.

REM Wait a moment before starting frontend
timeout /t 2 /nobreak >nul

REM Start Frontend Server
echo Starting Frontend Server...
start "RAG Frontend Server" cmd /k "cd /d "%PROJECT_ROOT%\web" && echo Starting React Frontend... && npm run dev"
echo Frontend server starting in new window...
echo.

REM Display information
echo ========================================
echo   All Services Started!
echo ========================================
echo.
echo Services:
echo   - Qdrant Vector DB:  http://localhost:6333
echo   - MongoDB:           mongodb://localhost:27017
echo   - Backend API:       http://localhost:8000
echo   - Backend Docs:      http://localhost:8000/docs
echo   - Frontend:          http://localhost:5173 (check terminal for exact port)
echo.
echo Note: Backend and Frontend are running in separate command windows.
echo Close those windows to stop the servers.
echo.
pause

