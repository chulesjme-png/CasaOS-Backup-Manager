import logging
from types import SimpleNamespace
from typing import Optional, Dict, Any

from app.core.backends.duplicati_backend import DuplicatiBackend
from app.models.backup_execution_request import BackupExecutionRequest
from app.models.backend_configuration import BackendConfiguration
from app.models.backup_configuration import BackupConfiguration
from app.models.backup_operation import BackupOperationType
from app.services.preflight_service import preflight_service
from app.services.db_hook_service import db_hook_service

logger = logging.getLogger("casaos-backup")

class DuplicatiOrchestratorService:
    """
    Servicio de orquestación completa para la ejecución de backups con Duplicati,
    integrando Pre-flight Checks y DB Hooks.
    """

    def __init__(self):
        self.backend = DuplicatiBackend()

    def run_app_backup(
        self,
        app_name: str,
        app_path: str,
        target_disk_path: str,
        duplicati_job_id: int,
        duplicati_url: str = "http://localhost:8200",
        duplicati_password: str = "MiContraseñaSegura2026"
    ) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de backup para una aplicación o sistema.
        """
        logger.info(f"🚀 [Orchestrator] Iniciando secuencia de backup para: {app_name}")

        # 1. Pre-flight Check (Validación de espacio)
        is_ok, msg = preflight_service.check_disk_space(
            target_path=target_disk_path,
            required_bytes_estimate=1 * 1024 * 1024 * 1024,  # Estimación base 1GB
            safety_margin_gb=5.0
        )
        if not is_ok:
            logger.error(f"❌ [Orchestrator] Fallo en pre-check de espacio: {msg}")
            return {"success": False, "error": msg}

        dump_path: Optional[str] = None
        try:
            # 2. DB Hook (Volcado previo de BD si aplica)
            dump_path = db_hook_service.create_db_dump(app_name=app_name, app_path=app_path)
            if dump_path:
                logger.info(f"📦 [Orchestrator] Volcado SQL generado en: {dump_path}")

            # 3. Solicitud de ejecución a Duplicati
            request = BackupExecutionRequest(
                backend_name="duplicati",
                operation=BackupOperationType.RUN_BACKUP,
                manifest=SimpleNamespace(application=app_name),
                backend_configuration=BackendConfiguration(
                    backend_name="duplicati",
                    configuration={
                        "url": duplicati_url,
                        "password": duplicati_password,
                        "timeout": 30
                    }
                ),
                backup_configuration=BackupConfiguration(
                    options={"backup_id": duplicati_job_id}
                )
            )

            result = self.backend.execute(request)

            if not result.success:
                logger.error(f"❌ [Orchestrator] Error en la ejecución de Duplicati: {result.errors}")
                return {"success": False, "errors": result.errors}

            logger.info(f"✅ [Orchestrator] Tarea {duplicati_job_id} iniciada correctamente en Duplicati.")
            return {
                "success": True,
                "execution_reference": result.execution_reference.dict() if (result.execution_reference and hasattr(result.execution_reference, "dict")) else str(result.execution_reference),
                "metadata": result.metadata
            }

        except Exception as e:
            logger.error(f"❌ [Orchestrator Exception] Error inesperado: {e}")
            return {"success": False, "error": str(e)}

        finally:
            # 4. Cleanup (Eliminar volcados temporales)
            db_hook_service.cleanup_db_dump(app_path=app_path)

duplicati_orchestrator = DuplicatiOrchestratorService()
duplicati_service = duplicati_orchestrator