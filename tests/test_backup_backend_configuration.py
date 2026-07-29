from app.core.backends.null_backup_backend import (
    NullBackupBackend,
)

from app.models.backend_configuration import (
    BackendConfiguration,
)

from app.models.backup_configuration import (
    BackupConfiguration,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_manifest import (
    BackupManifest,
)


def test_null_backend_receives_configuration():

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    backup_configuration = BackupConfiguration(
        destination_url="file:///tmp/test-backup",
    )

    configuration = BackendConfiguration(
        backend_name="null",
        configuration={
            "test_option": True
        },
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="null",
        backend_configuration=configuration,
    )

    backend = NullBackupBackend()

    result = backend.execute(request)

    assert result.success is True

    assert (
        request.backend_configuration.configuration[
            "test_option"
        ]
        is True
    )