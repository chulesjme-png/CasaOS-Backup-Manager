import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import jinja2

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# DIAGNÓSTICO DE ESTRUCTURA DE ARCHIVOS EN LOGS
# ------------------------------------------------------------------------------
logger.info("=== RASTREANDO ARCHIVOS EN EL CONTENEDOR ===")
for root, dirs, files in os.walk("/app"):
    html_files = [f for f in files if f.endswith(".html")]
    if html_files:
        logger.info(f"📂 Plantillas encontradas en '{root}': {html_files}")

from app.database.connection import engine, Base, get_db
from app.routers import api_backends, api_executions, api_schedules, api_restore
from app.services.scheduler_service import start_scheduler, stop_scheduler

# Creación automática de tablas en SQLite
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="CasaOS Backup Manager",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------------------------------------------------------
# CONFIGURACIÓN DE PLANTILLAS Y ESTÁTICOS MULTI-RUTA
# ------------------------------------------------------------------------------
# Búsqueda exhaustiva en todas las ubicaciones posibles del contenedor
search_dirs = [
    "/app/app/templates",
    "/app/templates",
    "/app",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")
]

valid_dirs = [d for d in search_dirs if os.path.isdir(d)]

# Jinja2 buscará 'dashboard.html' en todas estas rutas hasta encontrarlo
templates = Jinja2Templates(directory=valid_dirs[0] if valid_dirs else "/app")
templates.env.loader = jinja2.FileSystemLoader(valid_dirs)

# Manejo seguro de archivos estáticos
static_dirs = ["/app/app/static", "/app/static"]
for s_dir in static_dirs:
    os.makedirs(s_dir, exist_ok=True)
    if os.path.exists(s_dir):
        app.mount("/static", StaticFiles(directory=s_dir), name="static")
        break

# Registro de Routers API
app.include_router(api_backends.router)
app.include_router(api_executions.router)
app.include_router(api_schedules.router)
app.include_router(api_restore.router)


# ------------------------------------------------------------------------------
# RUTAS DE INTERFAZ WEB (HTML)
# ------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def read_dashboard(request: Request, db: Session = Depends(get_db)):
    """Renderiza el dashboard principal."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/schedules", response_class=HTMLResponse)
def read_schedules(request: Request):
    """Renderiza la vista de gestión de programaciones."""
    return templates.TemplateResponse("schedules.html", {"request": request})


@app.get("/restore", response_class=HTMLResponse)
def read_restore(request: Request):
    """Renderiza la vista de restauración de respaldos."""
    return templates.TemplateResponse("restore.html", {"request": request})