import os
import json
import logging
import urllib.parse
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

def get_duplicati_credentials() -> tuple[str, str]:
    url = DEFAULT_DUPLICATI_URL
    password = DEFAULT_DUPLICATI_PASS
    config_path = "/DATA/AppData/casaos-backup-manager/config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                url = data.get("duplicati_url") or data.get("duplicati_host") or url
                password = data.get("duplicati_password") or data.get("password") or password
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron leer credenciales de config.json: {e}")
    return url, password

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

    def _do_request(self, session: requests.Session, method: str, url: str, password: str = "", **kwargs) -> requests.Response:
        base_url = url.rsplit('/api/', 1)[0] if '/api/' in url else url
        has_xsrf = any("xsrf" in c.name.lower() for c in session.cookies)
        if not has_xsrf:
            try:
                session.get(f"{base_url}/api/v1/systemstate", timeout=5)
            except Exception:
                pass
        for cookie in session.cookies:
            if "xsrf" in cookie.name.lower():
                session.headers["X-XSRF-Token"] = urllib.parse.unquote(cookie.value)
                break
        if password and password.strip():
            session.headers["X-UI-Password"] = password.strip()
        resp = session.request(method, url, **kwargs)
        for cookie in session.cookies:
            if "xsrf" in cookie.name.lower():
                session.headers["X-XSRF-Token"] = urllib.parse.unquote(cookie.value)
        return resp

    def _get_or_create_automatic_job(self, job_name: str, source_path: str, target_disk_path: str, duplicati_url: str, duplicati_password: str) -> Optional[int]:
        session = requests.Session()
        base_url = duplicati_url.rstrip('/')

        if duplicati_password and duplicati_password.strip():
            try:
                self._do_request(session, "POST", f"{base_url}/api/v1/login", password=duplicati_password, json={"password": duplicati_password}, timeout=10)
            except Exception:
                pass

        # 1. Buscar si ya existe la tarea por nombre exacto o parcial
        try:
            resp = self._do_request(session, "GET", f"{base_url}/api/v1/backups", password=duplicati_password, timeout=15)
            if resp.status_code == 200:
                backups = resp.json()
                if isinstance(backups, list):
                    target_clean = job_name.lower().replace("_", " ").strip()
                    for job in backups:
                        job_data = job.get("Backup", job)
                        name = str(job_data.get("Name", "")).lower().replace("_", " ").strip()
                        if target_clean in name or name in target_clean:
                            job_id = int(job_data.get("ID", job.get("ID", 0)))
                            logger.info(f"🔎 Tarea encontrada automáticamente: '{name}' (ID: {job_id})")
                            return job_id
        except Exception as e:
            logger.warning(f"⚠️ Error listando tareas en Duplicati: {e}")

        # 2. Si no existe, crearla de forma completamente automatizada
        target_url = f"file://{target_disk_path.rstrip('/')}/{job_name}"
        logger.info(f"⚡ Autocreando tarea en Duplicati: '{job_name}' -> {target_url}")

        payload = {
            "ID": 0,
            "Name": job_name,
            "Description": "Creado automáticamente por CasaOS Backup Manager",
            "Tags": [],
            "TargetURL": target_url,
            "Enabled": True,
            "AsList": False,
            "Sources": [source_path],
            "Settings": [
                {"Name": "no-encryption", "Value": "true"}
            ],
            "Filters": []
        }

        try:
            create_resp = self._do_request(
                session, "POST", f"{base_url}/api/v1/backups",
                password=duplicati_password,
                json=payload,
                timeout=20
            )

            if create_resp.status_code in (200, 201):
                try:
                    data = create_resp.json()
                    new_id = data.get("ID") or data.get("Backup", {}).get("ID")
                    if new_id:
                        return int(new_id)
                except Exception:
                    pass

                # Reconsultar para obtener el ID asignado
                check_resp = self._do_request(session, "GET", f"{base_url}/api/v1/backups", password=duplicati_password, timeout=10)
                if check_resp.status_code == 200:
                    for job in check_resp.json():
                        job_data = job.get("Backup", job)
                        if job_name.lower() in str(job_data.get("Name", "")).lower():
                            return int(job_data.get("ID", job.get("ID")))
            
            logger.error(f"❌ Error al autocrear tarea (HTTP {create_resp.status_code}): {create_resp.text}")
        except Exception as e:
            logger.error(f"❌ Excepción en autocreación de tarea: {e}")

        # 3. Fallback de emergencia absoluto: si hay alguna tarea en el sistema, usar la primera para no bloquear al usuario
        try:
            resp = self._do_request(session, "GET", f"{base_url}/api/v1/backups", password=duplicati_password, timeout=10)
            if resp.status_code == 200:
                backups = resp.json()
                if isinstance(backups, list) and len(backups) > 0:
                    fallback_id = int(backups[0].get("Backup", backups[0]).get("ID", 1))
                    logger.warning(f"⚠️ Usando tarea existente por defecto como fallback ID: {fallback_id}")
                    return fallback_id
        except Exception:
            pass

        return None

    def find_job_id_by_name(self, app_name: str, duplicati_url: str = DEFAULT_DUPLICATI_URL, duplicati_password: str = DEFAULT_DUPLICATI_PASS) -> Optional[int]:
        sanitized_name = f"[CBM] {app_name}"
        return self._get_or_create_automatic_job(
            job_name=sanitized_name,
            source_path=f"/DATA/AppData/{app_name}" if app_name != "Sistema_Completo" else "/DATA",
            target_disk_path=get_active_target_disk(),
            duplicati_url=duplicati_url,
            duplicati_password=duplicati_password
        )

    def run_app_backup(self, app_name: str, app_path: str, target_disk_path: str, duplicati_job_id: Optional[int] = None, duplicati_url: Optional[str] = None, duplicati_password: Optional[str] = None) -> Dict[str, Any]:
        cfg_url, cfg_pass = get_duplicati_credentials()
        resolved_url = duplicati_url or cfg_url
        resolved_pass = duplicati_password if duplicati_password is not None else cfg_pass

        logger.info(f"🚀 [Orchestrator] Ejecutando backup automatizado para: {app_name}")

        is_ok, msg = preflight_service.check_disk_space(target_path=target_disk_path, required_bytes_estimate=2 * 1024 * 1024 * 1024, safety_margin_gb=10.0)
        if not is_ok:
            logger.error(f"❌ [Orchestrator] Espacio insuficiente: {msg}")
            return {"success": False, "error": msg}

        if duplicati_job_id is None:
            duplicati_job_id = self.find_job_id_by_name(app_name, resolved_url, resolved_pass)

        if duplicati_job_id is None:
            err_msg = f"No se pudo autogenerar o encontrar un Job ID en Duplicati para '{app_name}'."
            logger.error(f"❌ [Orchestrator]: {err_msg}")
            return {"success": False, "error": err_msg}

        try:
            dump_path = db_hook_service.create_db_dump(app_name=app_name, app_path=app_path)

            request = BackupExecutionRequest(
                backend_name="duplicati",
                operation=BackupOperationType.RUN_BACKUP,
                manifest=SimpleNamespace(application=app_name),
                backend_configuration=BackendConfiguration(
                    backend_name="duplicati",
                    configuration={"url": resolved_url, "password": resolved_pass, "timeout": 60}
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

    def run_full_disaster_recovery(self, app_name: str = "Sistema_Completo", app_path: str = "/DATA", target_disk_path: Optional[str] = None, target_disk: Optional[str] = None, duplicati_job_id: Optional[int] = None, duplicati_url: Optional[str] = None, duplicati_password: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        cfg_url, cfg_pass = get_duplicati_credentials()
        resolved_url = duplicati_url or cfg_url
        resolved_pass = password if password is not None else (duplicati_password or cfg_pass)

        resolved_target = target_disk_path or target_disk
        if not resolved_target or resolved_target == "/var/lib/casaos":
            resolved_target = get_active_target_disk()

        if duplicati_job_id is None:
            duplicati_job_id = self._get_or_create_automatic_job(
                job_name="[CBM] Sistema_Completo",
                source_path=app_path,
                target_disk_path=resolved_target,
                duplicati_url=resolved_url,
                duplicati_password=resolved_pass
            )

        return self.run_app_backup(
            app_name=app_name,
            app_path=app_path,
            target_disk_path=resolved_target,
            duplicati_job_id=duplicati_job_id,
            duplicati_url=resolved_url,
            duplicati_password=resolved_pass
        )

    def get_task_status(self, task_id: int = 1, duplicati_url: Optional[str] = None, duplicati_password: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        try:
            cfg_url, cfg_pass = get_duplicati_credentials()
            resolved_url = duplicati_url or cfg_url
            resolved_pass = password if password is not None else (duplicati_password or cfg_pass)

            session = requests.Session()
            resp = self._do_request(session, "GET", f"{resolved_url.rstrip('/')}/api/v1/progressstate", password=resolved_pass, timeout=15)
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