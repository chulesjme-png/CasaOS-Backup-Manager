import os
import logging
from pathlib import Path
from typing import Optional, Any, Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, status
from pydantic import BaseModel

from app.services.backup_engine_service import backup_engine_service

logger = logging.getLogger("casaos-backup")

router = APIRouter(prefix="/api/v1/backups", tags=["backups"])

DESTINATION_PATH = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa"


# ------------------------------------------------------------------------------
# SCHEMAS Flexible (Acepta cualquier nombre de clave desde el Frontend)
# ------------------------------------------------------------------------------

class RestorePayload(BaseModel):
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


# ------------------------------------------------------------------------------
# ENDPOINTS REST API
# ------------------------------------------------------------------------------

@router.get("/profiles")
def get_backup_profiles():
    """Escanea el directorio de aplicaciones y devuelve los perfiles disponibles."""
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


@router.post("/restore")
async def restore_backup_endpoint(payload: RestorePayload, request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint de restauración ultra-compatible con cualquier formato de JSON enviado por la interfaz.
    """
    # 1. Extraer el nombre del archivo desde cualquiera de los campos posibles
    file_identifier = (
        payload.snapshot_id
        or payload.backup_id
        or payload.filename
        or payload.file_name
        or payload.file
        or payload.id
        or payload.name
        or payload.path
    )

    # Fallback: si Pydantic no lo cazó, inspeccionar el diccionario JSON en bruto
    if not file_identifier:
        try:
            raw_body = await request.json()
            logger.info(f"🔍 [Restore] Contenido JSON recibido en bruto: {raw_body}")
            for k in ["snapshot_id", "backup_id", "filename", "file_name", "file", "id", "name", "path"]:
                if k in raw_body and raw_body[k]:
                    file_identifier = str(raw_body[k])
                    break
        except Exception as e:
            logger.warning(f"[Restore] No se pudo leer el cuerpo de la petición en bruto: {e}")

    if not file_identifier:
        logger.error("❌ [Restore Error 400] La petición no contiene ningún identificador de archivo válido.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se ha recibido el nombre o ID del archivo de backup a restaurar."
        )

    logger.info(f"🔄 [POST /api/v1/backups/restore] Solicitud recibida para: {file_identifier}")

    # 2. Localizar el archivo en el almacenamiento
    file_path = os.path.join(DESTINATION_PATH, file_identifier)
    
    if not os.path.exists(file_path):
        possible_path = Path(file_identifier)
        if possible_path.exists():
            file_path = str(possible_path)
        else:
            logger.error(f"❌ Archivo no encontrado en disco: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El archivo de backup '{file_identifier}' no existe en {DESTINATION_PATH}."
            )

    # 3. Detección del nombre de la app objetivo
    app_name = payload.app_name or payload.app
    if not app_name or app_name == "system":
        file_lower = file_identifier.lower()
        if "transmission" in file_lower:
            app_name = "transmission"
        elif "jellyfin" in file_lower:
            app_name = "jellyfin"
        elif "sonarr" in file_lower:
            app_name = "sonarr"
        elif "radarr" in file_lower:
            app_name = "radarr"
        elif "immich" in file_lower:
            app_name = "immich-postgres"
        elif "duplicati" in file_lower:
            app_name = "duplicati"
        elif "disasterrecovery" in file_lower:
            app_name = "disaster-recovery"
        else:
            app_name = file_identifier.split("_")[0]

    # 4. Lanzar orquestación en segundo plano (no bloquea la respuesta HTTP)
    background_tasks.add_task(
        backup_engine_service.execute_restore_1click,
        app_name=app_name,
        file_path=file_path,
        target_path=payload.target_path
    )

    return {
        "status": "ACCEPTED",
        "message": f"Restauración iniciada con éxito para {app_name}",
        "snapshot_id": file_identifier
    }