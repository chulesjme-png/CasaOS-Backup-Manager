"""
Cliente HTTP para la API de Duplicati.

Este módulo encapsula toda la comunicación con el servidor Duplicati.

Responsabilidades:

- Gestionar la conexión HTTP.
- Gestionar autenticación mediante tokens.
- Consultar el estado del servidor.
- Obtener información de la API.
- Lanzar excepciones propias de la aplicación.

No conoce el dominio del Backup Engine.
No conoce Docker.
No conoce CasaOS.
"""

from __future__ import annotations

from typing import Any

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
        """
        Inicializa el cliente.

        Args:

            base_url:
                URL base del servidor Duplicati.

            timeout:
                Timeout de las peticiones HTTP.

            password:
                Contraseña del servidor Duplicati.
        """

        self.base_url = base_url.rstrip("/")

        self.timeout = timeout

        self.password = password

        self.session: Session = requests.Session()

        self._access_token: str | None = None

        self._refresh_token: str | None = None

        self._authenticated = False



    def authenticate(self) -> bool:
        """
        Autentica contra Duplicati.

        Obtiene los tokens necesarios para
        realizar llamadas autenticadas.
        """

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

            raise ConnectorResponseError(
                str(exc)
            ) from exc



        except ValueError as exc:

            raise ConnectorResponseError(
                "La respuesta recibida no es un JSON válido."
            ) from exc



    def _ensure_authenticated(
        self,
    ) -> None:
        """
        Garantiza que existe autenticación válida.
        """

        if self._authenticated:
            return

        self.authenticate()



    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """
        Ejecuta una petición HTTP contra Duplicati.
        """

        self._ensure_authenticated()

        url = (
            f"{self.base_url}/"
            f"{endpoint.lstrip('/')}"
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

            raise ConnectorResponseError(
                str(exc)
            ) from exc


        except ValueError as exc:

            raise ConnectorResponseError(
                "La respuesta recibida no es un JSON válido."
            ) from exc



    def _get(
        self,
        endpoint: str,
    ) -> Any:
        """
        Ejecuta una petición GET.
        """

        return self._request(
            "GET",
            endpoint,
        )



    def ping(
        self,
    ) -> bool:
        """
        Comprueba disponibilidad del servidor Duplicati.
        """

        self.get_server_state()

        return True



    def get_server_state(
        self,
    ) -> dict[str, Any]:
        """
        Obtiene el estado del servidor Duplicati.
        """

        return self._get(
            "/api/v1/serverstate"
        )



    def get_version(
        self,
    ) -> str:
        """
        Devuelve la versión de Duplicati.
        """

        state = self.get_server_state()

        return state.get(
            "Version",
            "unknown",
        )