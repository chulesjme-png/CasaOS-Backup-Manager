from app.services.backend_configuration_service import (
    BackendConfigurationService,
)


def test_returns_duplicati_configuration():

    service = BackendConfigurationService()

    config = service.get_configuration("duplicati")

    assert config.backend_name == "duplicati"
    assert config.enabled is True
    assert "url" in config.configuration
    assert "timeout" in config.configuration


def test_returns_null_configuration():

    service = BackendConfigurationService()

    config = service.get_configuration("null")

    assert config.backend_name == "null"
    assert config.enabled is True


def test_unknown_backend_is_disabled():

    service = BackendConfigurationService()

    config = service.get_configuration("restic")

    assert config.enabled is False