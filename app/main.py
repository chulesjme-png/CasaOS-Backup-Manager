import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import jinja2

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
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="CasaOS Backup Manager",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------------------------------------------------------
# RESOLUCIÓN DE RUTAS ROBUSTA PARA PLANTILLAS Y ESTÁTICOS
# ------------------------------------------------------------------------------
# Definimos los posibles directorios donde pueden residir las plantillas
possible_template_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),            # /app/app/templates
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"), # /app/templates
    "/app/templates",
    "/app/app/templates"
]

# Filtramos solo las carpetas que realmente existen en el sistema de archivos del contenedor
valid_template_dirs = [d for d in possible_template_dirs if os.path.exists(d)]

logger.info(f"📁 Directorios de plantillas detectados: {valid_template_dirs}")

# Configuramos un Loader de Jinja2 multi-ruta
templates = Jinja2Templates(directory=valid_template_dirs[0] if valid_template_dirs else "/app/templates")
if valid_template_dirs:
    templates.env.loader = jinja2.FileSystemLoader(valid_template_dirs)

# Manejo seguro del directorio estático
possible_static_dirs = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"),
    "/app/static",
    "/app/app/static"
]
for s_dir in possible_static_dirs:
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