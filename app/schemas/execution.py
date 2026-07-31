"""
Esquemas Pydantic para las operaciones de ejecución de copias de seguridad.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BackupExecutionApiRequest(BaseModel):
    """
    Estructura para solicitar la ejecución de un backup vía API.
    """
    application: str = Field(..., description="Nombre de la aplicación a respaldar (ej. 'nextcloud')")
    sources: List[str] = Field(default_factory=list, description="Rutas de origen a incluir")
    excluded_sources: List[str] = Field(default_factory=list, description="Rutas de origen a excluir")
    backend_name: str = Field("duplicati", description="Nombre del backend a utilizar")
    destination_url: str = Field("file:///backups", description="URL o ruta de destino del backup")
    backup_id: Optional[str] = Field(None, description="ID del backup en el backend (requerido por Duplicati)")
    backend_url: str = Field("http://localhost:8200", description="URL base de la API del backend")
    backend_password: str = Field("", description="Contraseña de autenticación si aplica")


class BackupExecutionReferenceResponse(BaseModel):
    """
    Referencia ligera de la tarea iniciada.
    """
    execution_id: str
    task_id: Optional[str] = None
    backend: str


class BackupResultResponse(BaseModel):
    """
    Respuesta estandarizada del resultado de una operación.
    """
    success: bool
    backend: str
    application: str
    operation: str
    execution_reference: Optional[BackupExecutionReferenceResponse] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackupTaskStatusApiRequest(BaseModel):
    """
    Estructura para consultar el estado de una tarea o del servidor.
    """
    backend_name: str = Field("duplicati", description="Backend a consultar")
    backend_url: str = Field("http://localhost:8200", description="URL del backend")
    backend_password: str = Field("", description="Contraseña del backend")
    task_id: Optional[str] = Field(None, description="ID específico de la tarea (opcional)")


class BackupTaskCancelApiRequest(BaseModel):
    """
    Estructura para cancelar una tarea activa.
    """
    backend_name: str = Field("duplicati", description="Backend objetivo")
    backend_url: str = Field("http://localhost:8200", description="URL del backend")
    backend_password: str = Field("", description="Contraseña del backend")
    task_id: str = Field(..., description="ID de la tarea a cancelar")