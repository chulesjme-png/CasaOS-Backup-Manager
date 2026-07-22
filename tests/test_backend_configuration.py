from app.models.backend_configuration import BackendConfiguration


def test_backend_configuration_defaults():
    config = BackendConfiguration(
        backend_name="duplicati"
    )

    assert config.backend_name == "duplicati"
    assert config.enabled is True
    assert config.configuration == {}
    assert config.metadata == {}


def test_backend_configuration_custom_values():
    config = BackendConfiguration(
        backend_name="restic",
        enabled=False,
        configuration={
            "repository": "/backup/repo"
        },
        metadata={
            "version": "1.0"
        }
    )

    assert config.backend_name == "restic"
    assert config.enabled is False
    assert config.configuration["repository"] == "/backup/repo"
    assert config.metadata["version"] == "1.0"