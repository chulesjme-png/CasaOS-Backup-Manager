from unittest.mock import Mock

from app.models.backup_configuration import (
    BackupConfiguration,
)
from app.models.backup_plan import BackupPlan
from app.services.backup_plan_execution_service import (
    BackupPlanExecutionService,
)


def test_backup_plan_execution_service_prepares_execution():
    """
    Verifica que un BackupPlan genera una solicitud
    preparada para backend.
    """

    backup_job_builder = Mock()

    backup_job = Mock()

    backup_job_builder.build.return_value = backup_job

    backup_engine = Mock()

    manifest = Mock()

    backup_engine.prepare.return_value = manifest

    execution_request = Mock()
    execution_request.manifest = manifest
    execution_request.backend_name = "duplicati"

    backup_execution_service = Mock()
    backup_execution_service.prepare.return_value = (
        execution_request
    )

    backend_execution = Mock()

    backend = Mock()

    backend_execution.resolve.return_value = backend

    service = BackupPlanExecutionService(
        backup_job_builder_service=backup_job_builder,
        backup_engine_service=backup_engine,
        backup_execution_service=backup_execution_service,
        backend_execution_service=backend_execution,
    )

    backup_plan = Mock(spec=BackupPlan)

    backup_configuration = BackupConfiguration(
        destination_url="file:///backup"
    )

    result = service.execute(
        backup_plan=backup_plan,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
    )

    backup_job_builder.build.assert_called_once_with(
        backup_plan
    )

    backup_engine.prepare.assert_called_once_with(
        backup_job
    )

    backup_execution_service.prepare.assert_called_once_with(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
    )

    backend_execution.resolve.assert_called_once_with(
        execution_request
    )

    assert result["backend"] == backend
    assert result["request"] == execution_request