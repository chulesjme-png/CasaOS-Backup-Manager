import os
import logging
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, status
from pydantic import BaseModel

from app.core.config import config_manager
from app.core.ws_manager import ws_manager
from app.services.backup_engine_service import backup_engine_service

logger = logging.getLogger("casaos-backup")

router = APIRouter(prefix="/api/v1/backups", tags=["backups"])


def locate_backup_file(filename: str) -> Optional[str]:
    """
    Busca el archivo de backup en la ruta configurada, rutas habituales
    o mediante escaneo rápido en los puntos de montaje /media y /DATA.
    """
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename

    candidates = []
    
    cfg = config_manager.config
    if hasattr(cfg, "destination_path") and cfg.destination_path:
        candidates.append(cfg.destination_path)
    if hasattr(cfg, "backup_destination") and cfg.backup_destination:
        candidates.append(cfg.backup_destination)

    candidates.extend([
        "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa",
        "/DATA/AppData",
        "/DATA",
    ])

    for base in candidates:
        if not base:
            continue
        possible_file = os.path.join(base, filename)
        if os.path.exists(possible_file):
            return possible_file

    media_root = Path("/media")
    if media_root.exists():
        try:
            for match in media_root.glob(f"**/{filename}"):
                if match.is_file():
                    return str(match)
        except Exception as e:
            logger.warning(f"Error al escanear /media: {e}")

    return None


class RestorePayload(BaseModel):
    backup_file: Optional[str] = None
    target_app: Optional[str] = None
    snapshot_id: Optional[str] = None
    backup_id: Optional[str] = None
    filename: Optional[str] = None
    file_name: Optional[str] = None
    file: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    path: Optional[str] = None
    app_name: Optional[str] = None
    app: Optional[str] = None
    target_path: Optional[str] = None


@router.get("/profiles")
def get_backup_profiles():
    profiles = []
    base_path = "/DATA/AppData"
    search_path = base_path if os.path.exists(base_path) else "app/data/AppData"
    
    if os.path.exists(search_path):
        try:
            items = os.listdir(search_path)
            for item in items:
                item_path = os.path.join(search_path, item)
                if os.path.isdir(item_path):
                    profiles.append({
                        "name": item,
                        "app_name": item,
                        "path": item_path,
                        "status": "Protected"
                    })
        except Exception:
            pass
            
    if not profiles:
        profiles = [
            {"name": "duplicati", "app_name": "Duplicati", "path": "/DATA/AppData/duplicati", "status": "Protected"},
            {"name": "immich", "app_name": "Immich", "path": "/DATA/AppData/immich", "status": "Protected"},
            {"name": "plex", "app_name": "Plex", "path": "/DATA/AppData/plex", "status": "Protected"},
            {"name": "jellyfin", "app_name": "Jellyfin", "path": "/DATA/AppData/jellyfin", "status": "Protected"}
        ]
        
    return profiles


# Tarea de fondo con aviso de progreso y finalización vía WebSocket
async def task_execute_restore_with_ws(app_name: str, file_path: str, target_path: Optional[str]):
    try:
        # Notificar progreso inicial
        await ws_manager.broadcast({
            "type": "restore_progress",
            "status": "IN_PROGRESS",
            "percentage": 30,
            "message": f"Restaurando {app_name}..."
        })

        # Ejecutar la lógica de restauración sincrónica/asincrónica
        if asyncio.iscoroutinefunction(backup_engine_service.execute_restore_1click):
            await backup_engine_service.execute_restore_1click(app_name=app_name, file_path=file_path, target_path=target_path)
        else:
            await asyncio.to_thread(
                backup_engine_service.execute_restore_1click,
                app_name=app_name,
                file_path=file_path,
                target_path=target_path
            )

        # Notificar finalización exitosa al frontend
        logger.info(f"✨ [Restore] Notificando éxito de restauración vía WebSocket para {app_name}")
        await ws_manager.broadcast({
            "type": "restore_complete",
            "status": "COMPLETED",
            "percentage": 100,
            "message": f"Restauración de {app_name} completada con éxito."
        })
    except Exception as e:
        logger.error(f"❌ [Restore Error] Error en tarea de restauración: {e}")
        await ws_manager.broadcast({
            "type": "restore_error",
            "status": "FAILED",
            "percentage": 0,
            "message": f"Error restaurando {app_name}: {str(e)}"
        })


@router.post("/restore")
async def restore_backup_endpoint(payload: RestorePayload, request: Request, background_tasks: BackgroundTasks):
    file_identifier = (
        payload.backup_file
        or payload.snapshot_id
        or payload.backup_id
        or payload.filename
        or payload.file_name
        or payload.file
        or payload.id
        or payload.name
        or payload.path
    )

    if not file_identifier:
        try:
            raw_body = await request.json()
            for k in ["backup_file", "snapshot_id", "backup_id", "filename", "file_name", "file", "id", "name", "path"]:
                if k in raw_body and raw_body[k]:
                    file_identifier = str(raw_body[k])
                    break
        except Exception as e:
            logger.warning(f"[Restore] No se pudo leer el JSON en bruto: {e}")

    if not file_identifier:
        logger.error("❌ [Restore Error 400] Petición sin identificador de archivo.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se ha recibido el nombre del archivo de backup a restaurar."
        )

    logger.info(f"🔄 [POST /api/v1/backups/restore] Buscando archivo de respaldo: {file_identifier}")

    file_path = locate_backup_file(file_identifier)

    if not file_path:
        logger.error(f"❌ [Restore Error 404] No se encontró el archivo '{file_identifier}' en ninguna ruta conocida de almacenamiento.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El archivo '{file_identifier}' no se encuentra en el disco destino ni en el sistema."
        )

    logger.info(f"✅ Archivo localizado exitosamente en: {file_path}")

    app_name = payload.app_name or payload.app
    if not app_name or app_name in ["system", "all"]:
        file_lower = file_identifier.lower()
        if "sonarr" in file_lower:
            app_name = "sonarr"
        elif "radarr" in file_lower:
            app_name = "radarr"
        elif "transmission" in file_lower:
            app_name = "transmission"
        elif "jellyfin" in file_lower:
            app_name = "jellyfin"
        elif "immich" in file_lower:
            app_name = "immich-postgres"
        elif "duplicati" in file_lower:
            app_name = "duplicati"
        elif "disasterrecovery" in file_lower:
            app_name = "disaster-recovery"
        else:
            app_name = file_identifier.split("_")[0]

    # Añadir la tarea de fondo envolvente con WebSocket integrado
    background_tasks.add_task(
        task_execute_restore_with_ws,
        app_name=app_name,
        file_path=file_path,
        target_path=payload.target_path
    )

    return {
        "status": "ACCEPTED",
        "message": f"Restauración iniciada con éxito para {app_name}",
        "snapshot_id": file_identifier,
        "resolved_path": file_path
    }