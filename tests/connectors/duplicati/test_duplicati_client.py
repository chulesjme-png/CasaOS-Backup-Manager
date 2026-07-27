"""
Pruebas del DuplicatiClient.

Valida:

DuplicatiClient
        ↓
API REST Duplicati simulada
        ↓
Respuesta procesada
"""

from unittest.mock import Mock, patch

from app.connectors.duplicati.duplicati_client import (
    DuplicatiClient,
)


def test_authenticate_success():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    response = Mock()

    response.json.return_value = {
        "AccessToken": "token123",
        "RefreshNonce": "nonce123",
    }

    response.content = b"{}"

    with patch.object(
        client.session,
        "post",
        return_value=response,
    ):

        result = client.authenticate()

    assert result is True

    assert client._access_token == (
        "token123"
    )

    assert client._authenticated is True


def test_get_server_state_returns_data():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    client._authenticated = True

    response = Mock()

    response.content = b'{"Version":"2.0.8.1"}'

    response.json.return_value = {
        "Version": "2.0.8.1",
        "MachineName": "Duplicati",
    }

    with patch.object(
        client.session,
        "request",
        return_value=response,
    ):

        result = client.get_server_state()

    assert result["Version"] == (
        "2.0.8.1"
    )

    assert result["MachineName"] == (
        "Duplicati"
    )


def test_get_version_returns_version():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    with patch.object(
        client,
        "get_server_state",
        return_value={
            "Version": "2.0.8.1"
        },
    ):

        result = client.get_version()

    assert result == "2.0.8.1"


def test_create_job_sends_payload():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    client._authenticated = True

    with patch.object(
        client,
        "_post",
        return_value={
            "Backup": {
                "ID": "3",
            }
        },
    ) as mock_post:

        result = client.create_job(
            {
                "Backup": {
                    "Name": "Test",
                }
            }
        )

    assert result["Backup"]["ID"] == "3"

    mock_post.assert_called_once_with(
        "/api/v1/backups",
        {
            "Backup": {
                "Name": "Test",
            }
        },
    )


def test_get_backups_returns_list():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    client._authenticated = True

    backups = [
        {
            "Backup": {
                "ID": "1",
                "Name": "CasaOS Completo",
            }
        }
    ]

    with patch.object(
        client,
        "_get",
        return_value=backups,
    ):

        result = client.get_backups()

    assert isinstance(
        result,
        list,
    )

    assert result[0]["Backup"]["ID"] == (
        "1"
    )


def test_get_backup_returns_backup():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    client._authenticated = True

    backup = {
        "Backup": {
            "ID": "1",
            "Name": "CasaOS Completo",
        }
    }

    with patch.object(
        client,
        "_get",
        return_value=backup,
    ) as mock_get:

        result = client.get_backup(
            "1",
        )

    assert result["Backup"]["ID"] == (
        "1"
    )

    assert result["Backup"]["Name"] == (
        "CasaOS Completo"
    )

    mock_get.assert_called_once_with(
        "/api/v1/backups/1",
    )


def test_run_backup_starts_backup():

    client = DuplicatiClient(
        base_url="http://duplicati:8200",
        password="secret",
    )

    client._authenticated = True

    response = {
        "Status": "OK",
        "ID": 6,
    }

    with patch.object(
        client,
        "_post",
        return_value=response,
    ) as mock_post:

        result = client.run_backup(
            "1",
        )

    assert result["Status"] == (
        "OK"
    )

    assert result["ID"] == 6

    mock_post.assert_called_once_with(
        "/api/v1/backup/1/run",
    )