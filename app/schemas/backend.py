"""
Esquemas Pydantic para los Backends de Backup.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BackendCapabilitiesResponse(BaseModel):
    """
    Respuesta que describe las capacidades de un backend.
    """
    backend: str = Field(..., description="Nombre identificador del backend")
    version: str = Field(..., description="Versión del backend/proveedor")
    api_available: bool = Field(..., description="Indica si la API del backend está accesible")
    can_create_jobs: bool = Field(..., description="Soporta creación de trabajos")
    can_run_backup: bool = Field(..., description="Soporta ejecución de copias")
    can_get_status: bool = Field(..., description="Soporta consulta de estado")
    can_cancel_backup: bool = Field(..., description="Soporta cancelación")
    can_restore: bool = Field(..., description="Soporta restauración")
    can_verify: bool = Field(..., description="Soporta verificación")
    supports_encryption: bool = Field(..., description="Soporta cifrado")
    supports_compression: bool = Field(..., description="Soporta compresión")
    supports_retention: bool = Field(..., description="Soporta políticas de retención")
    supports_scheduling: bool = Field(..., description="Soporta programación")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadatos adicionales del proveedor")


class BackendInfoResponse(BaseModel):
    """
    Respuesta con la información básica de un backend registrado.
    """
    name: str
    capabilities: BackendCapabilitiesResponse