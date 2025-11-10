# Scripts Folder

This folder contains startup and shutdown scripts for the RAG application.

## Files

- **`start.ps1`** - PowerShell startup script (recommended)
- **`start.bat`** - Batch file startup script
- **`stop.ps1`** - PowerShell shutdown script
- **`stop.bat`** - Batch file shutdown script
- **`STARTUP_GUIDE.md`** - Complete documentation and troubleshooting guide

## Quick Start

**To start all services:**

```powershell
.\scripts\start.ps1
```

or

```cmd
scripts\start.bat
```

**To stop all services:**

```powershell
.\scripts\stop.ps1
```

or

```cmd
scripts\stop.bat
```

## What Gets Started

1. Qdrant vector database (Docker container on port 6333)
2. MongoDB database (Docker container on port 27017)
3. FastAPI backend server (port 8000)
4. React frontend dev server (port 5173)

See `STARTUP_GUIDE.md` for detailed documentation.

