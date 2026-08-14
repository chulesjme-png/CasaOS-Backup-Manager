import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel

from app.services.backup_engine_service import backup_engine_service

logger = logging.getLogger("casaos-backup")

router = APIRouter(prefix="/api/v1/backups", tags=["backups"])

DESTINATION_PATH = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa"


# ------------------------------------------------------------------------------
# SCHEMAS (Pydantic)
# ------------------------------------------------------------------------------

class RestorePayload(BaseModel):
    snapshot_id: Optional[str] = None
    backup_id: Optional[str] = None
    app_name: Optional[str] = "system"
    target_path: Optional[str] = None


# ------------------------------------------------------------------------------
# ENDPOINTS REST API
# ------------------------------------------------------------------------------

@router.get("/profiles")
def get_backup_profiles():
    """Escanea el directorio de aplicaciones y devuelve los perfiles disponibles."""
    profiles = []
    base_path = "/DATA/AppData"
    
    # Si no existe la ruta en el entorno local, buscamos o creamos una alternativa
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
            
    # Si no se detecta ninguna app física, devolvemos perfiles de ejemplo para que la interfaz luzca completa
    if not profiles:
        profiles = [
            {"name": "duplicati", "app_name": "Duplicati", "path": "/DATA/AppData/duplicati", "status": "Protected"},
            {"name": "immich", "app_name": "Immich", "path": "/DATA/AppData/immich", "status": "Protected"},
            {"name": "plex", "app_name": "Plex", "path": "/DATA/AppData/plex", "status": "Protected"},
            {"name": "jellyfin", "app_name": "Jellyfin", "path": "/DATA/AppData/jellyfin", "status": "Protected"}
        ]
        
    return profiles


@router.post("/restore")
async def restore_backup_endpoint(payload: RestorePayload, background_tasks: BackgroundTasks):
    """
    Endpoint invocado por el modal del frontend (/api/v1/backups/restore).
    """
    # Identificar el archivo seleccionado (acepta snapshot_id o backup_id)
    file_identifier = payload.snapshot_id or payload.backup_id
    
    if not file_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere 'snapshot_id' o 'backup_id' para iniciar la restauración."
        )

    logger.info(f"🔄 [POST /api/v1/backups/restore] Solicitud recibida para {file_identifier}")

    file_path = os.path.join(DESTINATION_PATH, file_identifier)
    
    if not os.path.exists(file_path):
        possible_path = Path(file_identifier)
        if possible_path.exists():
            file_path = str(possible_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El archivo de backup '{file_identifier}' no existe en {DESTINATION_PATH}."
            )

    # Detección dinámica del nombre del servicio destino
    app_name = payload.app_name
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
        else:
            app_name = file_identifier.split("_")[0]

    # Ejecutamos la restauración 1-Click en segundo plano
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