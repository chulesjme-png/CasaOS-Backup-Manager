import os
import json
import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Asegurar que el sistema reconozca correctamente los archivos SVG
mimetypes.add_type("image/svg+xml", ".svg")

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CasaOS-Backup-Manager")

app = FastAPI(
    title="CasaOS Backup Manager",
    version="v0.5.0-alpha7",
    description="Panel de administración de copias de seguridad para CasaOS y Raspberry Pi"
)

# -----------------------------------------------------------------------------
# RUTAS ABSOLUTAS DINÁMICAS
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Buscar la carpeta static (probar tanto app/static como static/)
static_dir = os.path.join(BASE_DIR, "static")
if not os.path.exists(static_dir):
    static_dir = os.path.join(BASE_DIR.parent, "static")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Configuración de plantillas Jinja2
templates_dir = os.path.join(BASE_DIR, "templates")
if not os.path.exists(templates_dir):
    templates_dir = os.path.join(BASE_DIR.parent, "templates")

templates = Jinja2Templates(directory=templates_dir)

# Configuración de persistencia local
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando config.json: {e}")
    return {"selected_target_disk": "", "duplicati_url": "http://localhost:8200", "retention_days": 30}

def save_config(config_data: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        logger.error(f"Error guardando config.json: {e}")

# -----------------------------------------------------------------------------
# MODELOS DE DATOS (Pydantic)
# -----------------------------------------------------------------------------
class ConfigModel(BaseModel):
    selected_target_disk: Optional[str] = None
    duplicati_url: Optional[str] = None
    retention_days: Optional[int] = None

class ScheduleModel(BaseModel):
    frequency: str
    time: str
    backup_type: str

class RestoreModel(BaseModel):
    snapshot_id: str

# -----------------------------------------------------------------------------
# RECURSOS DEL SISTEMA
# -----------------------------------------------------------------------------
def get_system_disks() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Disco: 08604ab9-10b8-46bc-a6f2-a19f3adfc6fa",
            "path": "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa",
            "free": "1712.5 GB",
            "total": "2740 GB"
        },
        {
            "name": "Almacenamiento Local CasaOS",
            "path": "/DATA",
            "free": "450.0 GB",
            "total": "1000 GB"
        }
    ]

def get_installed_apps() -> List[Dict[str, Any]]:
    return [
        {"name": "big-bear-adguard-home", "path": "/DATA/AppData/big-bear-adguard-home/data/work", "has_db_hook": False},
        {"name": "ddns-updater", "path": "/DATA/AppData/ddns-updater/data", "has_db_hook": False},
        {"name": "duplicati", "path": "/DATA", "has_db_hook": False},
        {"name": "immich", "path": "/var/lib/docker/volumes/immich_model_cache/_data", "has_db_hook": False},
        {"name": "jellyfin", "path": "/opt/vc/lib", "has_db_hook": False},
        {"name": "mariadb", "path": "/DATA/AppData/mariadb/config", "has_db_hook": True},
        {"name": "navidrome", "path": "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa/BibliotecaMusica", "has_db_hook": False},
        {"name": "nextcloud", "path": "/DATA/AppData/nextcloud/var/www/html", "has_db_hook": False},
        {"name": "nginxproxymanager", "path": "/DATA/AppData/nginxproxymanager/etc/letsencrypt", "has_db_hook": False},
        {"name": "plex", "path": "/media/pichules", "has_db_hook": False},
        {"name": "romantic_austin", "path": "/DATA/AppData/config", "has_db_hook": False},
        {"name": "transmission", "path": "/DATA/Downloads/watch", "has_db_hook": False},
        {"name": "wg-easy", "path": "/DATA/AppData/wg-easy/wireguard", "has_db_hook": False}
    ]

# -----------------------------------------------------------------------------
# VISTAS (ENDPOINTS HTML)
# -----------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    config = load_config()
    disks = get_system_disks()
    apps = get_installed_apps()
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": "v0.5.0-alpha7",
            "config": config,
            "disks": disks,
            "apps": apps
        }
    )

# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------
@app.post("/api/v1/config")
async def update_configuration(cfg: ConfigModel):
    current_config = load_config()
    if cfg.selected_target_disk is not None:
        current_config["selected_target_disk"] = cfg.selected_target_disk
    if cfg.duplicati_url is not None:
        current_config["duplicati_url"] = cfg.duplicati_url
    if cfg.retention_days is not None:
        current_config["retention_days"] = cfg.retention_days
        
    save_config(current_config)
    return {"status": "success", "config": current_config}

@app.post("/api/v1/backups/run-full")
async def run_full_backup(background_tasks: BackgroundTasks):
    logger.info("Iniciando copia de seguridad completa (Disaster Recovery)...")
    return {"status": "started", "type": "full", "message": "Resguardo completo del sistema en ejecución."}

@app.post("/api/v1/backups/run-app/{app_name}")
async def run_app_backup(app_name: str):
    logger.info(f"Iniciando copia de seguridad para app: {app_name}")
    return {"status": "started", "app": app_name, "message": f"Resguardo de {app_name} iniciado."}

@app.post("/api/v1/schedules")
async def create_schedule(schedule: ScheduleModel):
    logger.info(f"Programación guardada: {schedule.frequency} a las {schedule.time}")
    return {"status": "success", "schedule": schedule.dict()}

@app.get("/api/v1/backups/snapshots")
async def list_snapshots():
    snapshots = [
        {"id": "snap-2026-08-12-0300", "date": "2026-08-12 03:00", "type": "Full Disaster Recovery", "size": "42.5 GB"},
        {"id": "snap-2026-08-11-0300", "date": "2026-08-11 03:00", "type": "Full Disaster Recovery", "size": "41.8 GB"},
        {"id": "snap-2026-08-10-1700", "date": "2026-08-10 17:02", "type": "App Backup (mariadb)", "size": "1.2 GB"}
    ]
    return {"snapshots": snapshots}

@app.post("/api/v1/backups/restore")
async def restore_snapshot(restore_req: RestoreModel):
    logger.info(f"Restaurando copia {restore_req.snapshot_id}...")
    return {"status": "started", "snapshot_id": restore_req.snapshot_id}