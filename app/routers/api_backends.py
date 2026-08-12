from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()

class BackendConfig(BaseModel):
    name: str
    type: str  # e.g., 'duplicati', 'local', 's3'
    url: str
    is_active: bool = True

# Simulación de almacenamiento/DB temporal
MEMORY_BACKENDS_DB: List[Dict[str, Any]] = []

@router.get("/", response_model=List[Dict[str, Any]])
async def list_backends():
    """Lista todos los destinos de respaldo configurados."""
    return MEMORY_BACKENDS_DB

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_backend(backend: BackendConfig):
    """Registra un nuevo destino de respaldo."""
    new_backend = backend.dict()
    new_backend["id"] = len(MEMORY_BACKENDS_DB) + 1
    MEMORY_BACKENDS_DB.append(new_backend)
    return new_backend

@router.delete("/{backend_id}")
async def delete_backend(backend_id: int):
    """Elimina un destino de respaldo."""
    global MEMORY_BACKENDS_DB
    MEMORY_BACKENDS_DB = [b for b in MEMORY_BACKENDS_DB if b.get("id") != backend_id]
    return {"message": f"Destino {backend_id} eliminado exitosamente."}