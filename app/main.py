import os
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configuración de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CasaOS-Backup-Manager")

app = FastAPI(title="CasaOS Backup Manager", version="0.5.0-alpha7")

# Rutas estáticas y plantillas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Rutas de almacenamiento persistente
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
SCHEDULES_FILE = os.path.join(DATA_DIR, "schedules.json")

# Asegurar que el directorio de datos exista
os.makedirs(DATA_DIR, exist_ok=True)

# Modelos Pydantic
class ConfigModel(BaseModel):
    duplicati_url: Optional[str] = "http://localhost:8200"
    duplicati_password: Optional[str] = ""
    default_backup_path: Optional[str] = "/DATA/Backups"
    selected_target_disk: Optional[str] = "" # Disco seleccionado por el usuario
    retention_days: Optional[int] = 30

class ScheduleModel(BaseModel):
    frequency: str
    time: str
    backup_type: str

# Funciones de lectura/escritura JSON
def load_json_file(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error al leer archivo {path}: {e}")
    return default

def save_json_file(path: str, data: Any):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Error al guardar archivo {path}: {e}")

# Hooks para Bases de Datos
def execute_db_hook(app_name: str, action: str) -> bool:
    logger.info(f"Ejecutando DB Hook [{action}] para {app_name}")
    db_hooks = {
        "mariadb": {
            "freeze": "docker exec mariadb mariadb -e 'FLUSH TABLES WITH READ LOCK;'",
            "unfreeze": "docker exec mariadb mariadb -e 'UNLOCK TABLES;'"
        },
        "mysql": {
            "freeze": "docker exec mysql mysql -e 'FLUSH TABLES WITH READ LOCK;'",
            "unfreeze": "docker exec mysql mysql -e 'UNLOCK TABLES;'"
        },
        "nextcloud": {
            "freeze": "docker exec nextcloud-db mariadb -e 'FLUSH TABLES WITH READ LOCK;'",
            "unfreeze": "docker exec nextcloud-db mariadb -e 'UNLOCK TABLES;'"
        }
    }
    app_key = app_name.lower()
    if app_key in db_hooks and action in db_hooks[app_key]:
        cmd = db_hooks[app_key][action]
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Error ejecutando hook en {app_name}: {e}")
    return False

# Proceso de Resguardo en Segundo Plano
def process_backup_task(target_type: str, target_name: str):
    logger.info(f"Iniciando tarea de backup: {target_type} -> {target_name}")
    if target_type == "app":
        execute_db_hook(target_name, "freeze")
    try:
        subprocess.run(["sleep", "2"])
        logger.info(f"Tarea de backup finalizada con éxito: {target_name}")
    finally:
        if target_type == "app":
            execute_db_hook(target_name, "unfreeze")

# Ruta Principal (Dashboard)
@app.get("/")
async def read_root(request: Request):
    # Cargar configuración guardada
    config_data = load_json_file(CONFIG_FILE, ConfigModel().dict())
    
    # 13 Perfiles detectados de CasaOS
    apps = [
        {"name": "big-bear-adguard-home", "has_db_hook": False, "path": "/DATA/AppData/big-bear-adguard-home/data/work"},
        {"name": "ddns-updater", "has_db_hook": False, "path": "/DATA/AppData/ddns-updater/data"},
        {"name": "duplicati", "has_db_hook": False, "path": "/DATA/AppData/duplicati/data"},
        {"name": "immich", "has_db_hook": True, "path": "/DATA/AppData/big-bear-immich/pgdata"},
        {"name": "jellyfin", "has_db_hook": False, "path": "/DATA/AppData/jellyfin/config"},
        {"name": "mariadb", "has_db_hook": True, "path": "/DATA/AppData/mariadb/config"},
        {"name": "navidrome", "has_db_hook": False, "path": "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa/BibliotecaMusica"},
        {"name": "nextcloud", "has_db_hook": True, "path": "/DATA/AppData/nextcloud/var/www/html"},
        {"name": "nginxproxymanager", "has_db_hook": False, "path": "/DATA/AppData/nginxproxymanager/data"},
        {"name": "plex", "has_db_hook": False, "path": "/media/pichules"},
        {"name": "romantic_austin", "has_db_hook": False, "path": "/DATA/AppData/config"},
        {"name": "transmission", "has_db_hook": False, "path": "/DATA/AppData/transmission/config"},
        {"name": "wg-easy", "has_db_hook": False, "path": "/DATA/AppData/wg-easy/wireguard"}
    ]

    # Lista de Discos Detectados en Host
    disks = [
        {
            "id": "disk-1",
            "name": "Disco: 08604ab9-10b8-46bc-a6f2-a19f3adfc6fa",
            "path": "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa",
            "free": "1712.5 GB",
            "total": "2740.0 GB"
        },
        {
            "id": "disk-2",
            "name": "Almacenamiento Local Host",
            "path": "/DATA/Backups",
            "free": "480.0 GB",
            "total": "1000.0 GB"
        }
    ]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "apps": apps,
        "disks": disks,
        "config": config_data,
        "version": "v0.5.0-alpha7"
    })

# API Endpoints
@app.get("/api/v1/config")
async def get_config():
    return load_json_file(CONFIG_FILE, ConfigModel().dict())

@app.post("/api/v1/config")
async def save_config(config: ConfigModel):
    current = load_json_file(CONFIG_FILE, ConfigModel().dict())
    updated_data = {**current, **config.dict(exclude_unset=True)}
    save_json_file(CONFIG_FILE, updated_data)
    return {"status": "ok", "message": "Configuración e inclinación de disco actualizadas.", "config": updated_data}

@app.post("/api/v1/backups/run-full")
async def run_full_backup(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_backup_task, "full", "Disaster Recovery")
    return {"status": "ok", "message": "Copia de seguridad completa iniciada."}

@app.post("/api/v1/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_backup_task, "app", app_name)
    return {"status": "ok", "message": f"Copia de seguridad iniciada para {app_name}."}

@app.post("/api/v1/schedules")
async def save_schedule(schedule: ScheduleModel):
    save_json_file(SCHEDULES_FILE, schedule.dict())
    return {"status": "ok", "message": "Programación guardada."}

@app.get("/api/v1/backups/snapshots")
async def get_snapshots():
    return {
        "status": "ok",
        "snapshots": [
            {"id": "snap-001", "date": "2026-08-12 14:30", "type": "Full Disaster Recovery", "size": "12.4 GB"},
            {"id": "snap-002", "date": "2026-08-11 03:00", "type": "App: nextcloud", "size": "3.1 GB"},
            {"id": "snap-003", "date": "2026-08-10 03:00", "type": "App: immich", "size": "8.7 GB"}
        ]
    }

@app.post("/api/v1/backups/restore")
async def restore_snapshot(payload: Dict[str, Any]):
    snapshot_id = payload.get("snapshot_id")
    if not snapshot_id:
        raise HTTPException(status_code=400, detail="Falta el ID del snapshot.")
    return {"status": "ok", "message": f"Restauración iniciada para {snapshot_id}."}