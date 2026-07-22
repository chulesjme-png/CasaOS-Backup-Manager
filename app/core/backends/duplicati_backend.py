"""
Backend Duplicati.

Primera implementación del ecosistema
de backends reales del Backup Engine.

En esta fase:
- implementa el contrato BackupBackend
- genera BackupResult válido
- no ejecuta todavía Duplicati CLI

Las futuras versiones añadirán:
- detección de duplicati-cli
- construcción de comandos
- ejecución real
- captura de salida
- gestión avanzada de errores
"""

from datetime import datetime

from app.core.backends.backup_backend import (
    BackupBackend,
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

    def execute(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        """
        Ejecuta un backup mediante Duplicati.

        Actualmente funciona en modo simulación
        para validar la integración del backend.
        """

        started_at = datetime.utcnow()

        finished_at = datetime.utcnow()

        configuration = {}

        if request.backend_configuration:
            configuration = (
                request.backend_configuration.configuration
            )

        return BackupResult(
            success=True,
            backend=self.name,
            application=request.manifest.application,
            started_at=started_at,
            finished_at=finished_at,
            bytes_processed=0,
            warnings=[
                "Duplicati backend running in simulation mode."
            ],
            errors=[],
            metadata={
                "configuration": configuration,
            },
        )