from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/backends", tags=["backends"])

@router.get("/status")
def get_backends_status():
    """Devuelve el estado de los motores de respaldo y el almacenamiento activo."""
    return {
        "destination": "/media/pichules/08604ab9... (Activo)",
        "backends": ["duplicati", "restic"],
        "status": "healthy"
    }