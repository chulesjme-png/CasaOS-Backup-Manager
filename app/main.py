import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

# Importar enrutadores existentes del proyecto
from app.routers import (
    api_backends,
    api_executions,
    api_health,
    api_restore,
    api_schedules,
    dashboard,
    executions,
    backups,
)

app = FastAPI(
    title="CasaOS Backup Manager",
    description="Gestor de copias de seguridad para CasaOS",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Registrar la API v1 con /api
app.include_router(api_backends.router, prefix="/api/backends", tags=["Backends"])
app.include_router(api_schedules.router, prefix="/api/schedules", tags=["Schedules"])
app.include_router(api_executions.router, prefix="/api/executions", tags=["Executions"])
app.include_router(api_restore.router, prefix="/api/restore", tags=["Restore"])
app.include_router(api_health.router, prefix="/api/health", tags=["Health"])

# Registrar enrutadores de vistas HTML
app.include_router(dashboard.router)
app.include_router(executions.router)
app.include_router(backups.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}