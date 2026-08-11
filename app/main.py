import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database.connection import engine, Base, get_db
from app.routers import api_backends, api_executions, api_schedules, api_restore
from app.services.scheduler_service import start_scheduler, stop_scheduler

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Creación automática de tablas en SQLite
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio de servicios en background
    start_scheduler()
    yield
    # Apagado limpio
    stop_scheduler()


app = FastAPI(
    title="CasaOS Backup Manager",
    version="1.0.0",
    lifespan=lifespan
)

# Resolución dinámica de rutas absolutas para plantillas y estáticos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

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