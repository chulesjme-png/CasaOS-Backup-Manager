import os
import json
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
DEFAULT_DUPLICATI_PASS = os.getenv("DUPLICATI_PASSWORD", "")

def get_active_target_disk() -> str:
    config_path = "/DATA/AppData/casaos-backup-manager/config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                path = data.get("active_target_path") or data.get("target_disk")
                if path:
                    return path
        except Exception as e:
            logger.warning(f"⚠️ No se pudo leer config.json: {e}")
    return "/DATA"

class DuplicatiOrchestratorService:
    def __init__(self):
        self.backend = DuplicatiBackend()

    def _get_session(self, url: str, password: str) -> requests.Session:
        """Crea una sesión HTTP autenticada con Duplicati obteniendo el token XSRF."""
        session = requests.Session()
        base_url = url.rstrip('/')
        
        if password:
            try:
                login_resp = session.post(
                    f"{base_url}/api/v1/login", 
                    json={"password": password}, 
                    timeout=10
                )
                if login_resp.status_code == 200:
                    xsrf_token = login_resp.headers.get("X-XSRF-Token") or session.cookies.get("xsrf-token")
                    if xsrf_token:
                        session.headers.update({"X-XSRF-Token": xsrf_token})
            except Exception as e:
                logger.warning(f"⚠️ Error en autenticación con Duplicati: {e}")
                
        return session

    def find_job_id_by_name(
        self,
        app_name: str,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS
    ) -> Optional[int]:
        """Busca dinámicamente el ID del trabajo en Duplicati según el nombre."""
        try:
            session = self._get_session(duplicati_url, duplicati_password)
            resp = session.get(f"{duplicati_url.rstrip('/')}/api/v1/backups", timeout=15)
            
            if resp.status_code == 200:
                backups = resp.json()
                if isinstance(backups, list):
                    # Normalizar nombres para la búsqueda
                    target_name = app_name.lower().replace("_", " ").strip()
                    for job in backups:
                        job_name = str(job.get("Name", "")).lower().replace("_", " ").strip()
                        if target_name in job_name or job_name in target_name:
                            job_id = int(job.get("ID"))
                            logger.info(f"🔎 Encontrado Job ID {job_id} para '{app_name}' en Duplicati")
                            return job_id
                            
                    # Si solo hay 1 backup configurado en Duplicati, usarlo por defecto
                    if len(backups) == 1 and "ID" in backups[0]:
                        fallback_id = int(backups[0]["ID"])
                        logger.info(f"ℹ️ Usando el único Job ID {fallback_id} disponible en Duplicati ('{backups[0].get('Name')}')")
                        return fallback_id
            else:
                logger.error(f"❌ Error al consultar la API de Duplicati: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo listar los trabajos de Duplicati: {e}")
        
        return None

    def run_app_backup(
        self,
        app_name: str,
        app_path: str,
        target_disk_path: str,
        duplicati_job_id: Optional[int] = None,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS
    ) -> Dict[str, Any]:
        logger.info(f"🚀 [Orchestrator] Enviando orden de backup a Duplicati: {app_name}")

        is_ok, msg = preflight_service.check_disk_space(
            target_path=target_disk_path,
            required_bytes_estimate=2 * 1024 * 1024 * 1024,
            safety_margin_gb=10.0
        )
        if not is_ok:
            logger.error(f"❌ [Orchestrator] Espacio insuficiente: {msg}")
            return {"success": False, "error": msg}

        if duplicati_job_id is None:
            duplicati_job_id = self.find_job_id_by_name(app_name, duplicati_url, duplicati_password)

        if duplicati_job_id is None:
            err_msg = (
                f"No existe un trabajo configurado en Duplicati para '{app_name}'. "
                f"Crea una copia de seguridad en Duplicati (http://localhost:8200) llamada '{app_name}'."
            )
            logger.error(f"❌ [Orchestrator]: {err_msg}")
            return {"success": False, "error": err_msg}

        dump_path: Optional[str] = None
        try:
            dump_path = db_hook_service.create_db_dump(app_name=app_name, app_path=app_path)

            request = BackupExecutionRequest(
                backend_name="duplicati",
                operation=BackupOperationType.RUN_BACKUP,
                manifest=SimpleNamespace(application=app_name),
                backend_configuration=BackendConfiguration(
                    backend_name="duplicati",
                    configuration={
                        "url": duplicati_url,
                        "password": duplicati_password,
                        "timeout": 60
                    }
                ),
                backup_configuration=BackupConfiguration(
                    options={"backup_id": duplicati_job_id}
                )
            )

            result = self.backend.execute(request)
            if not result.success:
                return {"success": False, "errors": result.errors}

            return {
                "success": True,
                "job_id": duplicati_job_id,
                "execution_reference": result.execution_reference.dict() if hasattr(result.execution_reference, "dict") else str(result.execution_reference),
                "metadata": getattr(result, "metadata", {})
            }

        except Exception as e:
            logger.error(f"❌ [Orchestrator Exception]: {e}")
            return {"success": False, "error": str(e)}

        finally:
            db_hook_service.cleanup_db_dump(app_path=app_path)

    def run_full_disaster_recovery(
        self,
        app_name: str = "Sistema_Completo",
        app_path: str = "/DATA",
        target_disk_path: Optional[str] = None,
        target_disk: Optional[str] = None,
        duplicati_job_id: Optional[int] = None,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        resolved_target = target_disk_path or target_disk
        if not resolved_target or resolved_target == "/var/lib/casaos":
            resolved_target = get_active_target_disk()

        resolved_pass = password if password is not None else duplicati_password

        return self.run_app_backup(
            app_name=app_name,
            app_path=app_path,
            target_disk_path=resolved_target,
            duplicati_job_id=duplicati_job_id,
            duplicati_url=duplicati_url,
            duplicati_password=resolved_pass
        )

    def get_task_status(
        self,
        task_id: int = 1,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            resolved_pass = password if password is not None else duplicati_password
            session = self._get_session(duplicati_url, resolved_pass)

            resp = session.get(f"{duplicati_url.rstrip('/')}/api/v1/progressstate", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                
                if not data:
                    return {"status": "idle", "phase": "Idle", "progress": 0.0}

                phase = data.get("Phase", "Idle")
                progress = float(data.get("OverallProgress", 0.0)) * 100

                if phase in ["Completed", "Backup_Complete"]:
                    return {"status": "completed", "phase": phase, "progress": 100.0}

                if phase == "Idle":
                    return {"status": "idle", "phase": "Idle", "progress": 0.0}

                return {
                    "status": "running",
                    "phase": phase,
                    "progress": round(progress, 2),
                    "current_file": data.get("CurrentFilename", "")
                }

            return {"status": "error", "phase": f"HTTP {resp.status_code}", "progress": 0.0}
        except Exception as e:
            logger.error(f"⚠️ Error consultando API Duplicati: {e}")
            return {"status": "unknown", "phase": "Error", "progress": 0.0}

duplicati_orchestrator = DuplicatiOrchestratorService()