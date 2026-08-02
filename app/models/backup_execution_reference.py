"""
Referencia a una ejecución remota de backup.

Representa la identidad de un recurso gestionado por un backend
sin exponer detalles de su implementación.

Este modelo permite que el Backup Engine haga referencia a
trabajos, ejecuciones o recursos remotos de cualquier backend
(Duplicati, Restic, Borg, etc.) de forma uniforme.

No contiene lógica.
No conoce APIs REST.
No conoce implementaciones concretas.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.backup_resource_type import (
    BackupResourceType,
)


class BackupExecutionReference(BaseModel):
    """
    Referencia a un recurso remoto gestionado por un backend.
    """

    backend: str
    resource_type: BackupResourceType
    resource_id: str
    execution_id: Optional[str] = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(
        self,
        backend: str = "",
        resource_type: Any = BackupResourceType.TASK,
        resource_id: str = "",
        execution_id: Optional[str] = None,
        metadata: dict[str, Any] | None = None,
        **data: Any,
    ) -> None:
        if "resource_type" in data and isinstance(data["resource_type"], str):
            data["resource_type"] = BackupResourceType(data["resource_type"])
        super().__init__(
            backend=backend,
            resource_type=resource_type,
            resource_id=resource_id,
            execution_id=execution_id or resource_id,
            metadata=metadata or {},
            **data,
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "backend": self.backend,
            "resource_type": self.resource_type.value if hasattr(self.resource_type, "value") else str(self.resource_type),
            "resource_id": self.resource_id,
            "execution_id": self.execution_id,
            "metadata": self.metadata,
        }