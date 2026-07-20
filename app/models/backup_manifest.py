"""
Modelo de manifiesto de backup.

BackupManifest representa el contrato interno
entre el Backup Engine y los futuros backends.

No ejecuta operaciones.
No conoce implementaciones concretas.
"""

from datetime import datetime
from typing import Any

from app.models.storage_resource import StorageResource


class BackupManifest:
    """
    Representación inmutable de un backup preparado.
    """

    def __init__(
        self,
        application: str,
        sources: list[StorageResource],
        excluded_sources: list[StorageResource],
        warnings: list[str],
        estimated_size: int,
        metadata: dict[str, Any] | None = None,
        version: str = "1.0",
    ):
        self.application = application
        self.sources = sources
        self.excluded_sources = excluded_sources
        self.warnings = warnings
        self.estimated_size = estimated_size
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.version = version