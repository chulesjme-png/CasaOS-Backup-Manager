"""
Router de API para el diagnóstico de salud de la aplicación.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/v1/health",
    tags=["Health"],
)


class HealthResponse(BaseModel):
    status: str
    version: str


@router.get("", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Devuelve el estado de salud del servicio.
    """
    return HealthResponse(
        status="ok",
        version="1.0.0",
    )