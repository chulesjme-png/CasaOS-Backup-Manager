import os
import logging
import requests
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

DEFAULT_DUPLICATI_URL = os.getenv("DUPLICATI_URL", "http://172.17.0.1:8200")
DEFAULT_DUPLICATI_PASS = os.getenv("DUPLICATI_PASSWORD", "MiContraseñaSegura2026")

class DuplicatiOrchestratorService:
    """
    Servicio de orquestación completa para la ejecución de backups con Duplicati,
    integrando Pre-flight Checks, DB Hooks y tareas programadas de Disaster Recovery.
    """

    def __init__(self):
        self.backend = DuplicatiBackend()

    def run_app_backup(
        self,
        app_name: str,
        app_path: str,
        target_disk_path: str,
        duplicati_job_id: int,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS
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

    def run_full_disaster_recovery(
        self,
        app_name: str = "CasaOS System Disaster Recovery",
        app_path: str = "/var/lib/casaos",
        target_disk_path: str = "/var/lib/casaos",
        duplicati_job_id: int = 1
    ) -> Dict[str, Any]:
        """
        Ejecuta la tarea programada de Disaster Recovery para el sistema.
        """
        logger.info("🛡️ [Orchestrator] Iniciando Disaster Recovery programado")
        return self.run_app_backup(
            app_name=app_name,
            app_path=app_path,
            target_disk_path=target_disk_path,
            duplicati_job_id=duplicati_job_id
        )

    def get_task_status(
        self,
        task_id: int,
        duplicati_url: str = DEFAULT_DUPLICATI_URL
    ) -> Dict[str, Any]:
        """
        Obtiene el estado actual y porcentaje de progreso de una tarea en Duplicati.
        """
        try:
            resp = requests.get(f"{duplicati_url}/api/v1/progressstate", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                current_task = data.get("Task")
                if current_task and current_task.get("ID") == task_id:
                    phase = data.get("Phase", "Running")
                    progress = data.get("OverallProgress", 0.0) * 100
                    return {
                        "status": "running",
                        "phase": phase,
                        "progress": round(progress, 2),
                        "current_file": data.get("CurrentFilename", ""),
                        "backend_speed": data.get("BackendSpeed", 0)
                    }

            history_resp = requests.get(f"{duplicati_url}/api/v1/backup/{task_id}", timeout=5)
            if history_resp.status_code == 200:
                history_data = history_resp.json()
                last_result = history_data.get("Metadata", {}).get("LastBackupDate")
                return {
                    "status": "completed" if last_result else "idle",
                    "phase": "Completed" if last_result else "Idle",
                    "progress": 100.0 if last_result else 0.0
                }

            return {"status": "unknown", "phase": "Unknown", "progress": 0.0}

        except Exception as e:
            logger.error(f"⚠️ Error al consultar estado de tarea Duplicati #{task_id}: {e}")
            return {"status": "error", "message": str(e), "progress": 0.0}

duplicati_orchestrator = DuplicatiOrchestratorService()
duplicati_service = duplicati_orchestrator