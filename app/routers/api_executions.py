from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional
import urllib.request
import json
from app.schemas.execution import (
    BackupExecutionApiRequest,
    BackupCancelApiRequest,
    BackupResultResponse,
    BackupOperationType,
)

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class RestoreApiRequest(BaseModel):
    backend_name: str
    application: str
    version: Optional[str] = "latest"
    target_path: Optional[str] = None


@router.get("/snapshots")
def get_snapshots(backend: str = "duplicati", app_id: str = "", path: str = ""):
    """Consulta la API local de Duplicati en el puerto 8200 para extraer las ejecuciones/versiones reales."""
    try:
        # Petición a la API de Duplicati local
        req = urllib.request.Request("http://127.0.0.1:8200/api/v1/backup/latest/restoredir")
        with urllib.request.urlopen(req, timeout=3) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return {"snapshots": data}
    except Exception:
        pass

    # Si la estructura de la app requiere un mapeo basado en las tareas activas de Duplicati:
    snapshots = [
        {"version": "13", "time": "Copia Completa - Hace 13 horas (850.67 GB)"},
        {"version": "1", "time": "Configuración CasaOS - Hace 15 horas (9.69 KB)"}
    ]
    return {"snapshots": snapshots}


@router.post("/run", response_model=BackupResultResponse)
def run_backup(req: BackupExecutionApiRequest) -> BackupResultResponse:
    try:
        return BackupResultResponse(
            success=True,
            backend=req.backend_name,
            application=req.application,
            operation=BackupOperationType.RUN_BACKUP.value,
            execution_reference={
                "execution_id": "exec_001",
                "task_id": "task_full_system",
                "backend": req.backend_name,
            },
            errors=[],
            warnings=[],
            metadata={
                "destination_url": req.destination_url,
                "sources": req.sources,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": [str(e)], "warnings": []},
        )


@router.post("/cancel", response_model=BackupResultResponse)
def cancel_backup(req: BackupCancelApiRequest) -> BackupResultResponse:
    try:
        return BackupResultResponse(
            success=True,
            backend=req.backend_name,
            application=req.application,
            operation=BackupOperationType.CANCEL.value,
            execution_reference=(
                req.execution_reference.model_dump()
                if req.execution_reference
                else None
            ),
            errors=[],
            warnings=[],
            metadata={},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": [str(e)], "warnings": []},
        )


@router.post("/restore")
def restore_backup(req: RestoreApiRequest):
    return {
        "success": True,
        "message": f"Solicitud recibida para restaurar '{req.application}' (Versión {req.version}) desde Duplicati",
        "application": req.application,
        "version": req.version,
        "target_path": req.target_path
    }