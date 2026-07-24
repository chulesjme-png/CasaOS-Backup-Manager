from app.models.backup_operation import (
    BackupOperationType,
)


def test_backup_operation_types_exist():
    assert BackupOperationType.CREATE_JOB.value == "create_job"
    assert BackupOperationType.RUN_BACKUP.value == "run_backup"
    assert BackupOperationType.GET_STATUS.value == "get_status"
    assert BackupOperationType.CANCEL.value == "cancel"
    assert BackupOperationType.RESTORE.value == "restore"
    assert BackupOperationType.VERIFY.value == "verify"