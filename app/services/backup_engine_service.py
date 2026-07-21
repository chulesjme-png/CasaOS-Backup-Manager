"""
Servicio principal del Backup Engine.

Orquesta la preparación de un backup.

No ejecuta copias.
No interactúa con Docker.
No conoce backends concretos.

Su responsabilidad es coordinar
la generación de artefactos internos.
"""

from typing import Optional

from app.models.backup_job import BackupJob
from app.models.backup_manifest import BackupManifest

from app.services.backup_manifest_builder_service import (
    BackupManifestBuilderService,
)


class BackupEngineService:
    """
    Orquestador principal del motor de backup.
    """

    def __init__(
        self,
        manifest_builder: Optional[BackupManifestBuilderService] = None,
    ):
        self.manifest_builder = (
            manifest_builder
            or BackupManifestBuilderService()
        )

    def prepare(
        self,
        backup_job: BackupJob,
    ) -> BackupManifest:
        """
        Prepara un manifiesto a partir de un BackupJob.
        """

        return self.manifest_builder.build(
            backup_job
        )