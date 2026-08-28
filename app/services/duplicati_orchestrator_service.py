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

    def _get_session(self, url: str, password: str = "") -> requests.Session:
        """Crea una sesión HTTP autenticada con Duplicati."""
        session = requests.Session()
        base_url = url.rstrip('/')
        
        try:
            resp = session.get(f"{base_url}/api/v1/systemstate", timeout=10)
            xsrf = session.cookies.get("xsrf-token") or resp.headers.get("X-XSRF-Token")
            if xsrf:
                session.headers.update({"X-XSRF-Token": xsrf})
        except Exception as e:
            logger.debug(f"No se pudo obtener el estado inicial de Duplicati: {e}")

        if password and password.strip():
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

    def _get_or_create_disaster_recovery_job(
        self,
        source_path: str,
        target_disk_path: str,
        duplicati_url: str,
        duplicati_password: str
    ) -> Optional[int]:
        """Busca o crea automáticamente la tarea exclusiva para el Sistema Completo (Disaster Recovery)."""
        session = self._get_session(duplicati_url, duplicati_password)
        base_url = duplicati_url.rstrip('/')
        managed_job_name = "[CBM] Sistema_Completo"

        # 1. Comprobar si ya existe la tarea en Duplicati
        try:
            resp = session.get(f"{base_url}/api/v1/backups", timeout=15)
            if resp.status_code == 200:
                backups = resp.json()
                if isinstance(backups, list):
                    for job in backups:
                        job_name = str(job.get("Name", ""))
                        if job_name == managed_job_name or "[cbm]" in job_name.lower():
                            job_id = int(job.get("ID"))
                            logger.info(f"🔎 Encontrada tarea de sistema '{job_name}' (ID: {job_id})")
                            return job_id
        except Exception as e:
            logger.warning(f"⚠️ Error consultando tareas en Duplicati: {e}")

        # 2. Crear automáticamente la tarea apuntando a /DisasterRecovery
        disaster_recovery_target = os.path.join(target_disk_path.rstrip('/'), "DisasterRecovery")
        logger.info(f"🔨 Creando automáticamente la tarea '{managed_job_name}' en Duplicati -> {disaster_recovery_target}")
        
        payload = {
            "Name": managed_job_name,
            "Description": "Copia de Seguridad Completa del Sistema generada por CasaOS Backup Manager",
            "TargetURL": f"file://{disaster_recovery_target}/",
            "SourceFiles": [source_path],
            "Settings": [
                {"Name": "--no-encryption", "Value": "true"}
            ]
        }

        try:
            create_resp = session.post(f"{base_url}/api/v1/backups", json=payload, timeout=20)
            if create_resp.status_code in (200, 201):
                new_job = create_resp.json()
                job_id = int(new_job.get("ID") or new_job.get("id"))
                logger.info(f"✅ Tarea '{managed_job_name}' creada exitosamente con ID {job_id}")
                return job_id
            else:
                logger.error(f"❌ Error al crear la tarea en Duplicati (HTTP {create_resp.status_code}): {create_resp.text}")
        except Exception as e:
            logger.error(f"❌ Excepción al aprovisionar tarea en Duplicati: {e}")

        return None

    def find_job_id_by_name(
        self,
        app_name: str,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS
    ) -> Optional[int]:
        """Busca el ID de un trabajo existente sin crear nuevos."""
        try:
            session = self._get_session(duplicati_url, duplicati_password)
            resp = session.get(f"{duplicati_url.rstrip('/')}/api/v1/backups", timeout=15)
            if resp.status_code == 200:
                backups = resp.json()
                if isinstance(backups, list):
                    target_name = app_name.lower().replace("_", " ").strip()
                    for job in backups:
                        job_name = str(job.get("Name", "")).lower().replace("_", " ").strip()
                        if target_name in job_name or job_name in target_name:
                            return int(job.get("ID"))
        except Exception as e:
            logger.warning(f"⚠️ Excepción buscando Job ID: {e}")
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
        logger.info(f"🚀 [Orchestrator] Enviando orden de backup para: {app_name}")

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
            err_msg = f"No se encontró un Job ID válido en Duplicati para '{app_name}'."
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

        # Auto-crear o recuperar la tarea única de Disaster Recovery
        if duplicati_job_id is None:
            duplicati_job_id = self._get_or_create_disaster_recovery_job(
                source_path=app_path,
                target_disk_path=resolved_target,
                duplicati_url=duplicati_url,
                duplicati_password=resolved_pass
            )

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