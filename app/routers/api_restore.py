import os
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel

from app.services.backup_engine_service import backup_engine_service

logger = logging.getLogger("casaos-backup")

router = APIRouter(prefix="/api/v1/restore", tags=["restore"])

DESTINATION_PATH = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa"


# ------------------------------------------------------------------------------
# SCHEMAS (Pydantic)
# ------------------------------------------------------------------------------

class BackupSnapshot(BaseModel):
    id: str
    app_name: str
    timestamp: str
    file_size: str
    file_path: str


class RestoreRequest(BaseModel):
    snapshot_id: str
    app_name: str
    target_path: Optional[str] = None


# ------------------------------------------------------------------------------
# ENDPOINTS REST API
# ------------------------------------------------------------------------------

@router.get("/snapshots", response_model=List[BackupSnapshot])
def list_snapshots():
    """Escanea el disco de destino y devuelve la lista de copias de seguridad disponibles para restaurar."""
    snapshots = []
    if not os.path.exists(DESTINATION_PATH):
        return snapshots

    try:
        for entry in os.listdir(DESTINATION_PATH):
            full_path = os.path.join(DESTINATION_PATH, entry)
            if os.path.isfile(full_path) and (entry.endswith(".zip") or entry.endswith(".tar.gz") or "duplicati" in entry):
                stat = os.stat(full_path)
                size_mb = f"{stat.st_size / (1024 * 1024):.2f} MB"
                
                # Identificación básica del nombre del perfil
                app_name = "system_disaster_recovery"
                entry_lower = entry.lower()
                if "immich" in entry_lower:
                    app_name = "immich-postgres"
                elif "nextcloud" in entry_lower:
                    app_name = "nextcloud"
                elif "navidrome" in entry_lower:
                    app_name = "navidrome"
                elif "plex" in entry_lower:
                    app_name = "plex"
                elif "jellyfin" in entry_lower:
                    app_name = "jellyfin"
                elif "sonarr" in entry_lower:
                    app_name = "sonarr"
                elif "radarr" in entry_lower:
                    app_name = "radarr"

                snapshots.append(BackupSnapshot(
                    id=entry,
                    app_name=app_name,
                    timestamp=os.path.basename(full_path),
                    file_size=size_mb,
                    file_path=full_path
                ))
    except Exception as e:
        logger.error(f"Error listando snapshots de restauración: {e}")

    return snapshots


@router.post("/execute")
@router.post("/restore")  # ALIAS PARA SOLUCIONAR EL ERROR 404 DE LA INTERFAZ
async def execute_restore(payload: RestoreRequest, background_tasks: BackgroundTasks):
    """
    Inicia el proceso de recuperación de datos automatizado (1-Click)
    a partir de una copia seleccionada.
    """
    logger.info(f"🔄 Iniciando solicitud de restauración para {payload.app_name} desde {payload.snapshot_id}")
    
    file_path = os.path.join(DESTINATION_PATH, payload.snapshot_id)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El archivo de backup '{payload.snapshot_id}' no fue encontrado en el disco de destino."
        )

    # Delegamos la tarea de restauración al fondo para respuesta asíncrona inmediata
    background_tasks.add_task(
        backup_engine_service.execute_restore_1click,
        app_name=payload.app_name,
        file_path=file_path,
        target_path=payload.target_path
    )

    return {
        "status": "ACCEPTED",
        "message": f"Restauración automatizada iniciada para {payload.app_name}",
        "snapshot_id": payload.snapshot_id
    }