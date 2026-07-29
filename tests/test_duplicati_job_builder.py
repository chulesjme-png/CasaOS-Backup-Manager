"""
Pruebas del DuplicatiJobBuilder.
"""

from app.connectors.duplicati.duplicati_job_builder import (
    DuplicatiJobBuilder,
)

from app.models.backup_configuration import (
    BackupConfiguration,
)

from app.models.backup_manifest import (
    BackupManifest,
)

from app.models.storage_resource import (
    StorageResource,
)


def test_duplicati_job_builder_build():

    manifest = BackupManifest(
        application="immich",
        sources=[
            StorageResource(
                application="immich",
                source="/DATA/AppData/immich",
                destination="/app/data",
                storage_type="bind",
            ),
            StorageResource(
                application="immich",
                source="/DATA/Photos",
                destination="/photos",
                storage_type="bind",
            ),
        ],
        excluded_sources=[],
        warnings=[],
        estimated_size=1024,
        metadata={
            "origin": "CasaOS",
        },
    )

    configuration = BackupConfiguration(
        destination_url="file:///backup",
        description="Backup Immich",
        encryption="AES-256",
        passphrase="secret",
        compression="zip",
        retention_policy="7D",
        schedule={
            "repeat": "1D",
        },
        filters=[],
        options={
            "threads": 2,
        },
        metadata={},
    )

    builder = DuplicatiJobBuilder()

    job = builder.build(
        manifest,
        configuration,
    )

    assert job.name == "immich"

    assert job.source_paths == [
        "/DATA/AppData/immich",
        "/DATA/Photos",
    ]

    assert job.destination_url == (
        "file:///backup"
    )

    assert job.description == (
        "Backup Immich"
    )

    assert job.encryption == (
        "AES-256"
    )

    assert job.passphrase == (
        "secret"
    )

    assert job.compression == (
        "zip"
    )

    assert job.retention_policy == (
        "7D"
    )

    assert job.schedule == {
        "repeat": "1D",
    }

    assert job.options == {
        "threads": 2,
    }

    assert job.metadata == {
        "origin": "CasaOS",
    }