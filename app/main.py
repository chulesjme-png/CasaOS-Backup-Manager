import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI(title="CasaOS Backup Manager")

# Configurar rutas del sistema
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Montar archivos estáticos y plantillas
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- ENDPOINTS DE LA API (/api) ---

@app.get("/api/backends/")
async def get_backends():
    # Retorna la lista de destinos de respaldo (puedes conectar aquí tu BD)
    return []

@app.get("/api/schedules/")
async def get_schedules():
    # Retorna las tareas programadas
    return []

@app.get("/api/executions/")
async def get_executions():
    # Retorna el historial de ejecuciones
    return []

@app.post("/api/executions/run-manual")
async def run_manual_execution():
    # Lógica para iniciar respaldo manual
    return {"status": "success", "message": "Respaldo iniciado"}

# --- RUTAS DE NAVEGACIÓN (VISTAS HTML) ---

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/schedules", response_class=HTMLResponse)
async def read_schedules_page(request: Request):
    return templates.TemplateResponse("schedules.html", {"request": request})

@app.get("/restore", response_class=HTMLResponse)
async def read_restore_page(request: Request):
    return templates.TemplateResponse("restore.html", {"request": request})