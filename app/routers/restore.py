import os
import json
import subprocess
from fastapi import APIRouter, BackgroundTasks, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional
from app.services.borg_restore_service import borg_restore_service

router = APIRouter(prefix="/api/v1/borg/restore", tags=["Borg Restore"])

class DryRunRequest(BaseModel):
    repo_path: str
    archive_name: str
    passphrase: Optional[str] = None

@router.get("/archives")
async def list_borg_archives(repo_path: Optional[str] = Query(None)):
    """Obtiene la lista de snapshots de Borg dentro del repositorio indicado o por defecto."""
    if not repo_path:
        candidates = [
            "/DATA/Backups/DisasterRecovery/BorgRepo",
            "/host/DATA/Backups/DisasterRecovery/BorgRepo"
        ]
        for c in candidates:
            if os.path.exists(c):
                repo_path = c
                break

    if not repo_path or not os.path.exists(repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Repositorio Borg no encontrado. Verifique la ubicación en el disco."
        )

    env = os.environ.copy()
    env["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"] = "yes"
    env["BORG_RELOCATED_REPO_ACCESS_IS_OK"] = "yes"

    try:
        cmd = ["borg", "list", "--json", repo_path]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=20)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            archives = [
                {
                    "name": a.get("name"),
                    "time": a.get("time"),
                    "id": a.get("id")
                }
                for a in data.get("archives", [])
            ]
            return {"repo_path": repo_path, "archives": archives}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error consultando Borg: {res.stderr}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Excepción al listar snapshots: {str(e)}"
        )

@router.post("/dry-run", status_code=status.HTTP_202_ACCEPTED)
async def start_dry_run(payload: DryRunRequest, background_tasks: BackgroundTasks):
    """Lanza la simulación Dry-Run en segundo plano."""
    if borg_restore_service.restore_state["status"] == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una tarea de simulación/restauración en curso."
        )

    background_tasks.add_task(
        borg_restore_service.run_dry_run_simulation,
        repo_path=payload.repo_path,
        archive_name=payload.archive_name,
        passphrase=payload.passphrase
    )

    return {
        "message": "Simulación de verificación iniciada correctamente en segundo plano.",
        "archive_name": payload.archive_name
    }

@router.get("/status")
async def get_restore_status():
    """Consulta el estado del proceso de verificación/restauración."""
    return borg_restore_service.restore_state

@router.post("/cancel")
async def cancel_restore():
    """Cancela el proceso activo."""
    if not borg_restore_service.cancel_simulation():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay ningún proceso activo que se pueda cancelar."
        )
    return {"message": "Proceso cancelado correctamente."}