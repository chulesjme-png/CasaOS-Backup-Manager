from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.services.borg_restore_service import borg_restore_service

router = APIRouter(prefix="/api/v1/borg/restore", tags=["Borg Restore"])

class DryRunRequest(BaseModel):
    repo_path: str
    archive_name: str
    passphrase: Optional[str] = None

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