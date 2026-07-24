from app.models.duplicati_capabilities import DuplicatiCapabilities

from app.connectors.duplicati.duplicati_client import DuplicatiClient
from app.connectors.exceptions import ConnectorError


class DuplicatiCapabilityDetector:
    """
    Detecta las capacidades disponibles de una instalación Duplicati.

    Esta clase actúa como capa intermedia entre:
    
    DuplicatiClient
        |
        v
    Modelos del sistema
    """

    def __init__(self, client: DuplicatiClient):
        self.client = client

    def detect(self) -> DuplicatiCapabilities:
        """
        Ejecuta la detección de capacidades.
        """

        try:
            version = self.client.get_version()

            return DuplicatiCapabilities(
                available=True,
                version=version,
                supports_api=True,
                supports_cli=False,
            )

        except ConnectorError as error:

            return DuplicatiCapabilities(
                available=False,
                errors=[
                    str(error)
                ],
            )