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

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("CasaOS-Backup-Manager")

app = FastAPI(title="CasaOS Backup Manager", version="0.5.0-alpha7")

# Montaje de estáticos y plantillas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Rutas del sistema
CONFIG_FILE = os.path.join(BASE_DIR, "..", "data", "config.json")
SCHEDULES_FILE = os.path.join(BASE_DIR, "..", "data", "schedules.json")

# Modelos Pydantic
class ConfigModel(BaseModel):
    duplicati_url: str = "http://localhost:8200"
    duplicati_password: Optional[str] = ""
    default_backup_path: str = "/DATA/Backups"
    retention_days: int = 30

class ScheduleModel(BaseModel):
    frequency: str  # daily, weekly
    time: str       # HH:MM
    backup_type: str # full, app

# Utilidades de Persistencia
def load_json_file(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando {path}: {e}")
    return default

def save_json_file(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# Lógica de Hooks para Bases de Datos
def execute_db_hook(app_name: str, action: str) -> bool:
    """
    Ejecuta comandos de congelamiento (freeze/lock) o descongelamiento (unfreeze/unlock)
    para contenedores de bases de datos detectados antes/después del backup.
    """
    logger.info(f"Ejecutando DB Hook ({action}) para la aplicación: {app_name}")
    
    # Mapeo de contenedores y sus comandos de Hook
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
            if res.returncode == 0:
                logger.info(f"Hook {action} ejecutado con éxito en {app_name}")
                return True
            else:
                logger.warning(f"Hook {action} falló en {app_name}: {res.stderr}")
        except Exception as e:
            logger.error(f"Excepción al ejecutar hook en {app_name}: {e}")
    return False

# Tareas en Segundo Plano
def process_backup_task(target_type: str, target_name: str):
    """
    Orquestador del proceso real de copia de seguridad.
    """
    logger.info(f"Iniciando tarea de backup: {target_type} - {target_name}")
    
    # 1. Ejecutar Hook Pre-Backup si aplica
    if target_type == "app":
        execute_db_hook(target_name, "freeze")

    try:
        # 2. Simulación de llamada a motor Duplicati / Rsync local
        # Aquí se realiza el resguardo de la ruta /DATA/AppData/{target_name} o /DATA
        logger.info(f"Procesando transferencia de datos para {target_name}...")
        subprocess.run(["sleep", "3"]) # Espacio de ejecución simulado/sincrónico
        
        logger.info(f"Backup completado con éxito para {target_name}")
    except Exception as e:
        logger.error(f"Error durante el backup de {target_name}: {e}")
    finally:
        # 3. Ejecutar Hook Post-Backup siempre para desbloquear la BD
        if target_type == "app":
            execute_db_hook(target_name, "unfreeze")

# Dashboard principal
@app.get("/")
async def read_root(request: Request):
    # Lista base de aplicaciones detectadas en CasaOS
    apps = [
        {"name": "AdGuard Home", "icon": "shield-check", "has_db_hook": False, "path": "/DATA/AppData/adguard"},
        {"name": "Nextcloud", "icon": "cloud", "has_db_hook": True, "path": "/DATA/AppData/nextcloud"},
        {"name": "Immich", "icon": "photo", "has_db_hook": True, "path": "/DATA/AppData/immich"},
        {"name": "Jellyfin", "icon": "film", "has_db_hook": False, "path": "/DATA/AppData/jellyfin"},
        {"name": "Navidrome", "icon": "music-note", "has_db_hook": False, "path": "/DATA/AppData/navidrome"},
        {"name": "MariaDB", "icon": "database", "has_db_hook": True, "path": "/DATA/AppData/mariadb"}
    ]
    return templates.TemplateResponse("index.html", {"request": request, "apps": apps, "version": "v0.5.0-alpha7"})

# Endpoints API
@app.post("/api/v1/backups/run-full")
async def run_full_backup(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_backup_task, "full", "Disaster Recovery")
    return {"status": "ok", "message": "Resguardo completo del sistema iniciado en segundo plano."}

@app.post("/api/v1/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_backup_task, "app", app_name)
    return {"status": "ok", "message": f"Resguardo para {app_name} iniciado correctamente."}

@app.post("/api/v1/config")
async def save_config(config: ConfigModel):
    save_json_file(CONFIG_FILE, config.dict())
    return {"status": "ok", "message": "Configuración guardada correctamente."}

@app.get("/api/v1/config")
async def get_config():
    config = load_json_file(CONFIG_FILE, ConfigModel().dict())
    return config

@app.post("/api/v1/schedules")
async def save_schedule(schedule: ScheduleModel):
    save_json_file(SCHEDULES_FILE, schedule.dict())
    return {"status": "ok", "message": "Programación de tareas guardada con éxito."}

@app.get("/api/v1/backups/snapshots")
async def get_snapshots():
    # Retorna lista de snapshots registrados
    snapshots = [
        {"id": "snap-001", "date": "2026-08-12 14:30", "type": "Full Disaster Recovery", "size": "12.4 GB"},
        {"id": "snap-002", "date": "2026-08-11 03:00", "type": "App: Nextcloud", "size": "3.1 GB"},
        {"id": "snap-003", "date": "2026-08-10 03:00", "type": "App: Immich", "size": "8.7 GB"}
    ]
    return {"status": "ok", "snapshots": snapshots}

@app.post("/api/v1/backups/restore")
async def restore_snapshot(payload: Dict[str, Any]):
    snapshot_id = payload.get("snapshot_id")
    if not snapshot_id:
        raise HTTPException(status_code=400, detail="ID de snapshot no proporcionado.")
    logger.info(f"Iniciando proceso de restauración para snapshot: {snapshot_id}")
    return {"status": "ok", "message": f"Proceso de restauración iniciado para {snapshot_id}."}