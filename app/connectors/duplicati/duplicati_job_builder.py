"""
Constructor del modelo interno de trabajos de Duplicati.

Responsabilidad:

Traducir el contrato interno del Backup Engine
(BackupManifest + BackupConfiguration)
al modelo DuplicatiJob.

No conoce HTTP.
No conoce la API REST.
No ejecuta operaciones.
"""

from app.models.backup_configuration import (
    BackupConfiguration,
)
from app.models.backup_manifest import (
    BackupManifest,
)
from app.models.duplicati_job import (
    DuplicatiJob,
)


class DuplicatiJobBuilder:
    """
    Construye un DuplicatiJob a partir del
    contrato interno del Backup Engine.
    """

    def build(
        self,
        manifest: BackupManifest,
        backup_configuration: BackupConfiguration,
    ) -> DuplicatiJob:
        """
        Construye un trabajo interno de Duplicati.
        """

        return DuplicatiJob(
            name=manifest.application,
            source_paths=[
                resource.source
                for resource in manifest.sources
            ],
            destination_url=(
                backup_configuration.destination_url
            ),
            description=(
                backup_configuration.description
            ),
            encryption=(
                backup_configuration.encryption
            ),
            passphrase=(
                backup_configuration.passphrase
            ),
            compression=(
                backup_configuration.compression
            ),
            retention_policy=(
                backup_configuration.retention_policy
            ),
            schedule=(
                backup_configuration.schedule
            ),
            options=dict(
                backup_configuration.options
            ),
            metadata=dict(
                manifest.metadata
            ),
        )