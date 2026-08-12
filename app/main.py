import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Importación de enrutadores del proyecto
from app.routers import (
    api_backends,
    api_schedules,
    api_executions,
    api_restore,
    api_health,
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

# Enrutadores API REST (con prefijo /api/v1)
app.include_router(api_backends.router, prefix="/api/v1/backends", tags=["Backends"])
app.include_router(api_schedules.router, prefix="/api/v1/schedules", tags=["Schedules"])
app.include_router(api_executions.router, prefix="/api/v1/executions", tags=["Executions"])
app.include_router(api_restore.router, prefix="/api/v1/restore", tags=["Restore"])
app.include_router(api_health.router, prefix="/api/v1/health", tags=["Health"])

# Enrutadores para las vistas HTML del Dashboard
app.include_router(dashboard.router)
app.include_router(executions.router)
app.include_router(backups.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}