"""
Construye un DuplicatiJob a partir de un BackupManifest.
"""

from app.models.backup_manifest import BackupManifest
from app.models.duplicati_job import DuplicatiJob


class DuplicatiJobBuilder:
    """
    Convierte un BackupManifest en un DuplicatiJob.
    """

    def build(
        self,
        manifest: BackupManifest,
    ) -> DuplicatiJob:
        """
        Construye un trabajo de Duplicati.
        """

        return DuplicatiJob(
            name=manifest.application,
            source_paths=[],
            destination_url="",
            description="",
            options={},
            metadata={},
        )