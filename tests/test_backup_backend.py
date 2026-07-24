from app.core.backends import NullBackupBackend

from app.models.backup_operation import (
    BackupOperationType,
)


def test_null_backup_backend():

    backend = NullBackupBackend()

    assert backend.name == "null"


def test_null_backup_backend_supports_run_backup():

    backend = NullBackupBackend()

    assert backend.supports_operation(
        BackupOperationType.RUN_BACKUP
    ) is True


def test_null_backup_backend_does_not_support_restore():

    backend = NullBackupBackend()

    assert backend.supports_operation(
        BackupOperationType.RESTORE
    ) is False