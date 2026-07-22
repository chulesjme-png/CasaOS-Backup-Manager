from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backend_configuration import (
    BackendConfiguration,
)

from app.models.backup_manifest import (
    BackupManifest,
)


def create_test_manifest():
    return BackupManifest(
        application="test",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )


def test_backup_execution_request_creates_default_configuration():

    manifest = create_test_manifest()

    request = BackupExecutionRequest(
        manifest,
        "null",
    )

    assert request.backend_name == "null"
    assert request.backend_configuration.backend_name == "null"


def test_backup_execution_request_accepts_configuration():

    manifest = create_test_manifest()

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={
            "destination": "/backup"
        },
    )

    request = BackupExecutionRequest(
        manifest,
        "duplicati",
        configuration,
    )

    assert request.backend_configuration.backend_name == "duplicati"
    assert request.backend_configuration.configuration["destination"] == "/backup"