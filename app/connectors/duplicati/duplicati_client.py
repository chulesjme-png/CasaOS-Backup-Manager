"""
Cliente HTTP para la API de Duplicati.

Este módulo encapsula toda la comunicación con el servidor Duplicati.

Responsabilidades:

- Gestionar la conexión HTTP.
- Gestionar autenticación mediante tokens.
- Consultar el estado del servidor.
- Obtener información de la API.
- Enviar payloads a la API REST.
- Lanzar excepciones propias de la aplicación.

No conoce el dominio del Backup Engine.
No conoce Docker.
No conoce CasaOS.
"""

from __future__ import annotations

from typing import Any
import json

import requests

from requests import Session
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import Timeout

from app.connectors.exceptions import (
    ConnectorResponseError,
    ConnectorTimeoutError,
    DuplicatiConnectionError,
)


class DuplicatiClient:
    """
    Cliente para la API REST de Duplicati.
    """

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        password: str = "",
    ) -> None:

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.password = password

        self.session: Session = requests.Session()

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._authenticated = False

    def authenticate(
        self,
    ) -> bool:

        try:

            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "password": self.password,
                },
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

            self._access_token = (
                data.get("AccessToken")
                or data.get("accessToken")
            )

            self._refresh_token = (
                data.get("RefreshToken")
                or data.get("refreshToken")
            )

            if not self._access_token:

                raise ConnectorResponseError(
                    "Duplicati no devolvió AccessToken."
                )

            self.session.headers.update(
                {
                    "Authorization": (
                        f"Bearer {self._access_token}"
                    )
                }
            )

            self._authenticated = True

            return True

        except ConnectionError as exc:

            raise DuplicatiConnectionError(
                str(exc)
            ) from exc

        except Timeout as exc:

            raise ConnectorTimeoutError(
                str(exc)
            ) from exc

        except HTTPError as exc:

            response = exc.response

            details = ""

            if response is not None:
                details = response.text

            raise ConnectorResponseError(
                f"{exc}. Response: {details}"
            ) from exc

        except ValueError as exc:

            raise ConnectorResponseError(
                "La respuesta recibida no es un JSON válido."
            ) from exc

    def _ensure_authenticated(
        self,
    ) -> None:

        if self._authenticated:
            return

        self.authenticate()

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:

        self._ensure_authenticated()

        url = (
            f"{self.base_url}/"
            f"{endpoint.lstrip('/')}"
        )

        if kwargs.get("json") is not None:

            print("\n===== DUPLICATI REQUEST =====")
            print(
                f"{method} {url}"
            )

            print(
                json.dumps(
                    kwargs["json"],
                    indent=4,
                    default=str,
                )
            )

            print(
                "=============================\n"
            )

        try:

            response = self.session.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs,
            )

            if response.status_code == 401:

                self._authenticated = False

                self.authenticate()

                response = self.session.request(
                    method=method,
                    url=url,
                    timeout=self.timeout,
                    **kwargs,
                )

            response.raise_for_status()

            if not response.content:
                return None

            return response.json()

        except ConnectionError as exc:

            raise DuplicatiConnectionError(
                str(exc)
            ) from exc

        except Timeout as exc:

            raise ConnectorTimeoutError(
                str(exc)
            ) from exc

        except HTTPError as exc:

            response = exc.response

            details = ""

            if response is not None:

                details = response.text

                print(
                    "\n===== DUPLICATI ERROR RESPONSE ====="
                )

                print(
                    f"STATUS: {response.status_code}"
                )

                print(
                    details
                )

                print(
                    "====================================\n"
                )

            raise ConnectorResponseError(
                f"{exc}. Response: {details}"
            ) from exc

        except ValueError as exc:

            raise ConnectorResponseError(
                "La respuesta recibida no es un JSON válido."
            ) from exc

    def _get(
        self,
        endpoint: str,
    ) -> Any:

        return self._request(
            "GET",
            endpoint,
        )

    def _post(
        self,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:

        if payload is None:

            return self._request(
                "POST",
                endpoint,
            )

        return self._request(
            "POST",
            endpoint,
            json=payload,
        )

    def ping(
        self,
    ) -> bool:

        self.get_server_state()

        return True

    def get_server_state(
        self,
    ) -> dict[str, Any]:

        return self._get(
            "/api/v1/serverstate"
        )

    def get_version(
        self,
    ) -> str:

        state = self.get_server_state()

        return state.get(
            "Version",
            "unknown",
        )

    def create_job(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        return self._post(
            "/api/v1/backups",
            payload,
        )

    def get_backups(
        self,
    ) -> list[dict[str, Any]]:

        response = self._get(
            "/api/v1/backups"
        )

        if response is None:
            return []

        return response

    def run_backup(
        self,
        backup_id: int,
    ) -> dict[str, Any]:

        return self._post(
            f"/api/v1/backup/{backup_id}/run",
        )

    def get_task(
        self,
        task_id: int,
    ) -> dict[str, Any]:

        return self._get(
            f"/api/v1/task/{task_id}"
        )

    def get_tasks(
        self,
    ) -> list[dict[str, Any]]:

        response = self._get(
            "/api/v1/tasks"
        )

        if response is None:
            return []

        return response

    def stop_task(
        self,
        task_id: int,
    ) -> None:

        self._post(
            f"/api/v1/task/{task_id}/stop"
        )

    def abort_task(
        self,
        task_id: int,
    ) -> None:

        self._post(
            f"/api/v1/task/{task_id}/abort"
        )