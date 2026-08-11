from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.config.settings import APP_DESCRIPTION, APP_NAME, APP_VERSION
from app.config.template import templates
from app.database.connection import init_db

# Importación de modelos para asegurar que SQLAlchemy cree todas las tablas
import app.models.execution  # noqa: F401

# Importación de Routers
from app.routers.dashboard import router as dashboard_router
from app.routers.api_v1 import router as api_v1_router
from app.routers.api_backends import router as backends_router
from app.routers.api_executions import router as executions_router
from app.routers.api_health import router as health_router
from app.routers.backups import router as backups_router
from app.routers.api_schedules import router as schedules_router

# Importaciones para el registro de backends y el programador
from app.core.backends.backend_registry import BackendRegistry
from app.core.backends.duplicati_backend import DuplicatiBackend
from app.services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializa las tablas de SQLite en la base de datos al arrancar
    init_db()
    
    # Registrar backends por defecto al iniciar la app
    registry = BackendRegistry()
    if "duplicati" not in registry.available():
        registry.register(DuplicatiBackend())
        
    # Iniciar motor de tareas programadas en segundo plano
    start_scheduler()

    yield

    # Detener el motor al apagar la app
    stop_scheduler()


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)

# Archivos estáticos
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

# ------------------------------------------------------------------------------
# VISTAS UI (Jinja2)
# ------------------------------------------------------------------------------

@app.get("/schedules")
def schedules_page(request: Request):
    return templates.TemplateResponse("schedules.html", {"request": request})

# ------------------------------------------------------------------------------
# ROUTERS
# ------------------------------------------------------------------------------

# 1. UI Router (Vistas HTML / Jinja2)
app.include_router(dashboard_router)

# 2. REST API v1 Router (Endpoints unificados para frontend)
app.include_router(api_v1_router)

# 3. REST API Routers adicionales (Salud, Backends, Ejecuciones, Backups, Schedules)
app.include_router(health_router)
app.include_router(backends_router)
app.include_router(executions_router)  # Incluido directamente sin prefix adicional
app.include_router(backups_router)
app.include_router(schedules_router)