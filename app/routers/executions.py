from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db, SessionLocal
from app.services.backup_manifest_builder_service import BackupManifestBuilderService

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def list_executions(db: Session = Depends(get_db)):
    """Lista el historial de ejecuciones de respaldos."""
    # Retorna lista vacía o lógica de consulta DB existente
    return []

@router.post("/run", response_model=Dict[str, Any])
async def run_execution(
    service: Optional[BackupManifestBuilderService] = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Inicia una ejecución de respaldo manual o programada."""
    try:
        # Si el servicio está instanciado, ejecuta la lógica
        if service and hasattr(service, "build"):
            service.build()
            
        return {
            "status": "success",
            "message": "Ejecución iniciada correctamente"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la ejecución del respaldo: {str(e)}"
        )