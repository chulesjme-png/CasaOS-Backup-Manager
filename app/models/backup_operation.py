from enum import Enum


class BackupOperationType(Enum):
    """
    Operaciones que un backend de backup puede ejecutar.
    """

    CREATE_JOB = "create_job"
    RUN_BACKUP = "run_backup"
    GET_STATUS = "get_status"
    CANCEL = "cancel"
    RESTORE = "restore"
    VERIFY = "verify"