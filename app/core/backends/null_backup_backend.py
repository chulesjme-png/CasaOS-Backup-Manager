"""
Backend nulo de pruebas.

No realiza ninguna copia real.
Sirve para validar el pipeline completo
del Backup Engine.

Implementa el contrato BackupBackend.
"""

from datetime import datetime

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


class NullBackupBackend(BackupBackend):
    """
    Backend de prueba que simula
    una ejecución correcta.
    """

    @property
    def name(self) -> str:
        """
        Nombre identificador del backend.
        """

        return "null"


    @property
    def capabilities(self) -> BackendCapabilities:
        """
        Capacidades del backend nulo.

        Este backend solo existe para pruebas
        del pipeline interno.
        """

        return BackendCapabilities(
            backend=self.name,
            version="test",
            api_available=False,
            can_create_jobs=False,
            can_run_backup=True,
            can_cancel_backup=False,
            can_restore=False,
            supports_encryption=False,
            supports_compression=False,
            supports_retention=False,
            supports_scheduling=False,
            metadata={
                "purpose": "testing",
            },
        )


    def execute(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        """
        Simula una ejecución de backup
        devolviendo un resultado válido.
        """

        started_at = datetime.utcnow()

        finished_at = datetime.utcnow()

        return BackupResult(
            success=True,
            backend=self.name,
            application=request.manifest.application,
            started_at=started_at,
            finished_at=finished_at,
            bytes_processed=0,
            warnings=[],
            errors=[],
            metadata={
                "message": "Null backend executed successfully."
            },
        )