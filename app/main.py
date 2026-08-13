import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import config_manager
from app.services.disk_service import disk_service
from app.services.discovery_service import discovery_service
from app.services.scheduler_service import scheduler_service
from app.api.v1.endpoints import router as api_v1_router
from app.routers import scheduler_router

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("casaos_backup_manager")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización y apagado."""
    logger.info("Iniciando CasaOS Backup Manager...")
    
    # Iniciar el planificador de tareas (APScheduler)
    scheduler_service.start()
    
    yield
    
    # Apagar el planificador de tareas al detener el contenedor
    logger.info("Deteniendo CasaOS Backup Manager...")
    scheduler_service.shutdown()


app = FastAPI(
    title="CasaOS Backup Manager",
    version=config_manager.config.version,
    lifespan=lifespan
)

# Montar archivos estáticos y plantillas Jinja2
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Incluir rutas API v1 y Scheduler
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(scheduler_router.router)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Ruta principal que sirve la interfaz web dashboard."""
    config = config_manager.config
    disks = disk_service.get_system_disks()
    apps = discovery_service.scan_apps()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "version": config.version,
            "config": config.model_dump(),
            "disks": disks,
            "apps": apps
        }
    )