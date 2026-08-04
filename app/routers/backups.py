from fastapi import APIRouter, HTTPException
from app.services.backup_service import backup_service

router = APIRouter(prefix="/api/backups", tags=["Backups API"])

@router.post("/run/{app_id}")
async def trigger_backup(app_id: str):
    """Lanza la ejecución de backup manual de una App."""
    result = backup_service.execute_app_backup(app_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@router.get("/snapshots")
async def get_snapshots():
    """Lista las instantáneas disponibles en el sistema."""
    return {"snapshots": backup_service.list_snapshots()}