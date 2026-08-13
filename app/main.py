import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.core.config import config_manager
from app.services.disk_service import disk_service
from app.services.discovery_service import discovery_service
from app.services.scheduler_service import scheduler_service
from app.api.v1.endpoints import router as api_v1_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("casaos-backup")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando CasaOS Backup Manager...")
    scheduler_service.start()
    yield
    logger.info("Cerrando CasaOS Backup Manager...")
    scheduler_service.stop()

app = FastAPI(
    title="CasaOS Backup Manager",
    version=config_manager.config.version,
    lifespan=lifespan
)

# Obtener la ruta base del directorio 'app'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Servir archivos estáticos
static_path = os.path.join(BASE_DIR, "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

# Configurar motor de plantillas Jinja2
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Incluir API v1
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    config = config_manager.config
    disks = disk_service.get_system_disks()
    apps = discovery_service.scan_apps()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "version": config.version,
        "config": config.model_dump(),
        "disks": disks,
        "apps": apps
    })

if __name__ == "__main__":
    import uvicorn
    # Importante: app.main:app apunta a app/main.py
    uvicorn.run("app.main:app", host="0.0.0.0", port=8088, reload=True)