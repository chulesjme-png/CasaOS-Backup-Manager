from app.core.backends import NullBackupBackend


def test_null_backup_backend():

    backend = NullBackupBackend()

    assert backend.name == "null"
