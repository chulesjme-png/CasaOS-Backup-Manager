from app.core.backends import BackendRegistry, NullBackupBackend


def test_backend_registry():

    registry = BackendRegistry()

    backend = NullBackupBackend()

    registry.register(backend)

    assert "null" in registry.available()

    assert registry.get("null") == backend