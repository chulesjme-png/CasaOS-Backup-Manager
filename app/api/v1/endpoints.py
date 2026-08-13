from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict
from app.core.config import config_manager, AppConfig
from app.services.disk_service import disk_service
from app.services.discovery_service import discovery_service
from app.services.duplicati_service import duplicati_service

router = APIRouter()

@router.get("/config", response_model=AppConfig)
def get_config():
    return config_manager.config

@router.post("/config", response_model=AppConfig)
def update_config(payload: Dict[str, str]):
    for key, value in payload.items():
        config_manager.update_key(key, value)
    return config_manager.config

@router.get("/disks")
def get_disks():
    return disk_service.get_system_disks()

@router.get("/apps")
def get_apps():
    return discovery_service.scan_apps()

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    # Ejecuta el trabajo en segundo plano
    success = await duplicati_service.run_app_backup(app["name"], app["path"])
    return {"status": "success" if success else "failed", "app": app_name}

@router.post("/backups/run-full")
async def run_full_backup():
    success = await duplicati_service.run_full_disaster_recovery()
    return {"status": "success" if success else "failed"}