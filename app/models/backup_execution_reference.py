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

from typing import Any

from app.models.backup_resource_type import (
    BackupResourceType,
)


class BackupExecutionReference:
    """
    Referencia a un recurso remoto gestionado por un backend.
    """

    def __init__(
        self,
        backend: str,
        resource_type: BackupResourceType,
        resource_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:

        self.backend = backend

        self.resource_type = resource_type

        self.resource_id = resource_id

        self.metadata = metadata or {}

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "backend": self.backend,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "metadata": self.metadata,
        }