"""
Backend Duplicati.

Primera integración real con el servidor Duplicati.

Responsabilidades:

- Implementar el contrato BackupBackend.
- Consumir BackendConfiguration.
- Comunicarse con Duplicati mediante DuplicatiClient.
- Transformar la respuesta en BackupResult.

No contiene lógica HTTP.
No conoce Docker.
No conoce CasaOS.

La comunicación externa está delegada en:
app.connectors.duplicati.DuplicatiClient
"""

from datetime import datetime

from app.connectors.duplicati.duplicati_client import (
    DuplicatiClient,
)

from app.connectors.exceptions import (
    ConnectorError,
)

from app.core.backends.backup_backend import (
    BackupBackend,
)

from app.models.backend_capabilities import (
    BackendCapabilities,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_result import (
    BackupResult,
)


class DuplicatiBackend(BackupBackend):
    """
    Backend basado en Duplicati.
    """

    @property
    def name(self) -> str:
        """
        Nombre identificador del backend.
        """

        return "duplicati"


    @property
    def capabilities(self) -> BackendCapabilities:
        """
        Capacidades soportadas por Duplicati.
        """

        return BackendCapabilities(
            backend=self.name,
            version="unknown",
            api_available=True,
            can_create_jobs=True,
            can_run_backup=True,
            can_cancel_backup=True,
            can_restore=True,
            supports_encryption=True,
            supports_compression=True,
            supports_retention=True,
            supports_scheduling=True,
            metadata={
                "provider": "Duplicati",
            },
        )


    def execute(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        """
        Ejecuta una operación mediante Duplicati.

        Actualmente:

        - valida configuración;
        - autentica contra Duplicati;
        - consulta estado del servidor;
        - devuelve información en BackupResult.

        Todavía no lanza backups reales.
        """

        started_at = datetime.utcnow()

        warnings = []
        errors = []
        metadata = {}

        try:

            configuration = {}

            if request.backend_configuration:

                configuration = (
                    request.backend_configuration.configuration
                )


            url = configuration.get(
                "url"
            )

            if not url:

                raise ConnectorError(
                    "Duplicati URL no configurada"
                )


            timeout = configuration.get(
                "timeout",
                30,
            )


            password = configuration.get(
                "password",
                "",
            )


            client = DuplicatiClient(
                base_url=url,
                timeout=timeout,
                password=password,
            )


            server_state = client.get_server_state()


            metadata = {
                "duplicati_server_state": server_state,
                "duplicati_version": (
                    server_state.get(
                        "Version",
                        "unknown",
                    )
                ),
            }


            success = True


        except ConnectorError as exc:

            success = False

            errors.append(
                str(exc)
            )


        finished_at = datetime.utcnow()


        return BackupResult(
            success=success,
            backend=self.name,
            application=request.manifest.application,
            started_at=started_at,
            finished_at=finished_at,
            bytes_processed=0,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
        )