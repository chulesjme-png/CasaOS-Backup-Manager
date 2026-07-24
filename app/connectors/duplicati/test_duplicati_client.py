"""
Tests para DuplicatiClient.

Comprueba:

- inicialización del cliente
- consulta del estado del servidor
- obtención de versión
- errores de conexión
- errores de timeout
"""

from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests

from app.connectors.duplicati.duplicati_client import DuplicatiClient
from app.connectors.exceptions import ConnectorTimeoutError
from app.connectors.exceptions import DuplicatiConnectionError


class TestDuplicatiClient:
    """
    Tests del cliente HTTP de Duplicati.
    """

    def test_client_initialization(self):
        """
        Comprueba que el cliente se inicializa correctamente.
        """

        client = DuplicatiClient(
            base_url="http://192.168.1.10:8200/",
            timeout=15,
        )

        assert client.base_url == "http://192.168.1.10:8200"
        assert client.timeout == 15
        assert client.session is not None

    @patch.object(DuplicatiClient, "_get")
    def test_get_server_state(self, mock_get):
        """
        Comprueba la obtención del estado del servidor.
        """

        mock_get.return_value = {
            "Version": "2.0.8.1",
            "MachineName": "Duplicati",
        }

        client = DuplicatiClient(
            base_url="http://duplicati:8200",
        )

        result = client.get_server_state()

        assert result["Version"] == "2.0.8.1"
        assert result["MachineName"] == "Duplicati"

        mock_get.assert_called_once_with(
            "/api/v1/serverstate"
        )

    @patch.object(DuplicatiClient, "_get")
    def test_get_version(self, mock_get):
        """
        Comprueba que obtiene correctamente la versión.
        """

        mock_get.return_value = {
            "Version": "2.0.8.1",
        }

        client = DuplicatiClient(
            base_url="http://duplicati:8200",
        )

        version = client.get_version()

        assert version == "2.0.8.1"

    @patch.object(
        DuplicatiClient,
        "_request",
    )
    def test_connection_error(self, mock_request):
        """
        Comprueba que un error de conexión se transforma
        en una excepción propia.
        """

        mock_request.side_effect = DuplicatiConnectionError(
            "Servidor no disponible"
        )

        client = DuplicatiClient(
            base_url="http://duplicati:8200",
        )

        with pytest.raises(DuplicatiConnectionError):
            client.get_server_state()

    @patch.object(
        DuplicatiClient,
        "_request",
    )
    def test_timeout_error(self, mock_request):
        """
        Comprueba que un timeout se propaga correctamente.
        """

        mock_request.side_effect = ConnectorTimeoutError(
            "Tiempo agotado"
        )

        client = DuplicatiClient(
            base_url="http://duplicati:8200",
        )

        with pytest.raises(ConnectorTimeoutError):
            client.get_server_state()