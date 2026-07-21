"""
Servicio encargado de construir manifiestos
internos del Backup Engine.

Transforma un BackupJob preparado en un
BackupManifest consumible por los backends.

No ejecuta backups.
No conoce implementaciones concretas.
No interactúa con Docker.
"""

from app.models.backup_job import BackupJob
from app.models.backup_manifest import BackupManifest


class BackupManifestBuilderService:
    """
    Constructor de manifiestos de backup.
    """

    def build(
        self,
        backup_job: BackupJob,
    ) -> BackupManifest:
        """
        Genera un BackupManifest a partir de un BackupJob.
        """

        return BackupManifest(
            application=backup_job.application.name,
            sources=list(backup_job.sources),
            excluded_sources=list(
                backup_job.excluded_sources
            ),
            warnings=list(
                backup_job.warnings
            ),
            estimated_size=backup_job.estimated_size,
            metadata={
                **backup_job.metadata,
                "generated_from": "BackupJob",
            },
        )