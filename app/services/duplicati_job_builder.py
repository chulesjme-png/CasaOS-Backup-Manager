"""
Construye un DuplicatiJob a partir de un BackupManifest y una
BackupConfiguration.
"""

from app.models.backup_configuration import BackupConfiguration
from app.models.backup_manifest import BackupManifest
from app.models.duplicati_job import DuplicatiJob


class DuplicatiJobBuilder:
    """
    Convierte un BackupManifest y una BackupConfiguration
    en un DuplicatiJob.
    """

    def build(
        self,
        manifest: BackupManifest,
        configuration: BackupConfiguration,
    ) -> DuplicatiJob:
        """
        Construye un trabajo de Duplicati.
        """

        source_paths = [
            resource.validation_path
            for resource in manifest.sources
            if resource.validation_path
        ]

        return DuplicatiJob(
            name=manifest.application,

            source_paths=source_paths,

            destination_url=configuration.destination_url,

            description=configuration.description,

            encryption=configuration.encryption,

            passphrase=configuration.passphrase,

            compression=configuration.compression,

            retention_policy=configuration.retention_policy,

            schedule=configuration.schedule,

            options=dict(
                configuration.options
            ),

            metadata={
                "manifest_version": manifest.version,
                "estimated_size": manifest.estimated_size,
                **configuration.metadata,
            },
        )