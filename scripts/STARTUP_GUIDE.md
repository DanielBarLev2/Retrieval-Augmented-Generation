# RAG Application Startup Guide

This guide explains how to use the startup scripts to quickly launch all services needed for the Retrieval-Augmented Generation application.

## Prerequisites

Before running the startup scripts, ensure you have:

1. **Docker Desktop** installed and running
2. **Python 3.11** with dependencies installed (see main README.md)
3. **Node.js** and **npm** installed
4. **Frontend dependencies** installed (`cd web && npm install`)

## Quick Start

### Option 1: PowerShell Script (Recommended)

From the project root, double-click `scripts\start.ps1` or run from PowerShell:

```powershell
.\scripts\start.ps1
```

### Option 2: Batch File

From the project root, double-click `scripts\start.bat` or run from Command Prompt:

```cmd
scripts\start.bat
```

## What the Startup Scripts Do

1. ✅ Check if Docker is running
2. ✅ Start or create Qdrant container (port 6333)
3. ✅ Start or create MongoDB container (port 27017)
4. ✅ Launch FastAPI backend server in a new window
5. ✅ Launch React frontend dev server in a new window

## Stopping the Application

### Option 1: PowerShell Script

```powershell
.\scripts\stop.ps1
```

### Option 2: Batch File

```cmd
scripts\stop.bat
```

### Manual Stop

You can also manually:
- Close the backend and frontend terminal windows
- Stop Docker containers: `docker stop qdrant-rag mongo-rag`

## Access Points

After startup, you can access:

- **Frontend UI**: http://localhost:5173 (or check terminal for actual port)
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **MongoDB**: mongodb://localhost:27017

## Troubleshooting

### Docker Not Running

**Error**: `Docker is not running`

**Solution**: Start Docker Desktop and wait for it to fully initialize

### Port Already in Use

**Error**: Port conflicts (6333, 27017, 8000, 5173)

**Solution**: 
- Check for existing processes using those ports
- Stop conflicting services or containers
- Run `docker ps` to see running containers

### Backend Won't Start

**Error**: Python/uvicorn errors

**Solution**:
- Ensure you're in a Python environment with dependencies installed
- Check that `backend/requirements.txt` dependencies are installed
- Verify `.env` file exists with correct configuration

### Frontend Won't Start

**Error**: npm/node errors

**Solution**:
- Run `npm install` in the `web/` directory
- Check Node.js version compatibility
- Delete `node_modules` and reinstall if needed

### Container Already Exists

The scripts handle this automatically by starting existing containers instead of creating new ones.

To start fresh:

```bash
docker rm -f qdrant-rag mongo-rag
```

Then run the startup script again.

## Development Workflow

1. **First Time Setup**:
   ```bash
   # Backend
   cd backend
   conda create -n RAG python=3.11
   conda activate RAG
   pip install -r requirements.txt
   
   # Frontend
   cd ../web
   npm install
   ```

2. **Daily Development**:
   - Run `.\scripts\start.ps1` or `scripts\start.bat`
   - Code in your editor
   - Services auto-reload on file changes
   - When done, run `.\scripts\stop.ps1` or `scripts\stop.bat`

3. **Data Persistence**:
   - Docker containers persist data between restarts
   - MongoDB chat history is preserved
   - Qdrant vector embeddings are preserved

## Additional Notes

- The backend runs with `--reload` flag for hot-reloading during development
- The frontend runs in development mode with Vite's HMR (Hot Module Replacement)
- Docker containers are named `qdrant-rag` and `mongo-rag` for easy identification
- Containers are stopped but not removed by the shutdown scripts (for faster restart)

## Need Help?

- Check the main `README.md` for detailed setup instructions
- View backend API docs at http://localhost:8000/docs when running
- Check logs in the terminal windows for error messages

