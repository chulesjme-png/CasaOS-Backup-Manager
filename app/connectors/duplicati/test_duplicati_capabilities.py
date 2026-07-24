from unittest.mock import Mock

from app.connectors.duplicati.duplicati_capabilities import (
    DuplicatiCapabilityDetector,
)

from app.connectors.exceptions import DuplicatiConnectionError


def test_detect_available_duplicati():

    client = Mock()

    client.get_version.return_value = "2.0.8.1"

    detector = DuplicatiCapabilityDetector(client)

    capabilities = detector.detect()

    assert capabilities.available is True
    assert capabilities.version == "2.0.8.1"
    assert capabilities.supports_api is True
    assert capabilities.supports_cli is False


def test_detect_connection_failure():

    client = Mock()

    client.get_version.side_effect = DuplicatiConnectionError(
        "Duplicati unavailable"
    )

    detector = DuplicatiCapabilityDetector(client)

    capabilities = detector.detect()

    assert capabilities.available is False
    assert "Duplicati unavailable" in capabilities.errors[0]


def test_detect_without_version():

    client = Mock()

    client.get_version.return_value = None

    detector = DuplicatiCapabilityDetector(client)

    capabilities = detector.detect()

    assert capabilities.available is True
    assert capabilities.version is None