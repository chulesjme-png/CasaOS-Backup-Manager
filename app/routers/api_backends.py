"""
Router de API para la gestión y consulta de Backends de backup.
"""

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.services.backend_registry import BackendRegistry
from app.schemas.backend import BackendCapabilitiesResponse, BackendInfoResponse

router = APIRouter(
    prefix="/api/v1/backends",
    tags=["Backends"],
)


@router.get("", response_model=List[BackendInfoResponse])
def list_backends() -> List[BackendInfoResponse]:
    """
    Lista todos los backends de almacenamiento/backup registrados en el sistema.
    """
    registry = BackendRegistry()
    available_backends = registry.list_backends()
    
    result = []
    for backend_name in available_backends:
        try:
            backend = registry.get(backend_name)
            caps = backend.capabilities
            result.append(
                BackendInfoResponse(
                    name=backend.name,
                    capabilities=BackendCapabilitiesResponse(**caps.__dict__),
                )
            )
        except Exception:
            continue
            
    return result


@router.get("/{backend_name}", response_model=BackendInfoResponse)
def get_backend_info(backend_name: str) -> BackendInfoResponse:
    """
    Obtiene las capacidades y detalles de un backend específico por su nombre.
    """
    registry = BackendRegistry()
    try:
        backend = registry.get(backend_name)
        caps = backend.capabilities
        return BackendInfoResponse(
            name=backend.name,
            capabilities=BackendCapabilitiesResponse(**caps.__dict__),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backend '{backend_name}' no encontrado: {str(exc)}",
        )