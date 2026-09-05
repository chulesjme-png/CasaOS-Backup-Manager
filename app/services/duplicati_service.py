import os
import json
import logging
import urllib.parse
import requests
import subprocess
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
    """Obtiene URL y contraseña configuradas para Duplicati."""
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
    """Lee el disco activo directamente desde la configuración del sistema."""
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

    def _do_request(
        self,
        session: requests.Session,
        method: str,
        url: str,
        password: str = "",
        **kwargs
    ) -> requests.Response:
        """Realiza peticiones HTTP gestionando tokens XSRF y contraseña UI de Duplicati."""
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

    def _get_or_create_disaster_recovery_job(
        self,
        source_path: str,
        target_disk_path: str,
        duplicati_url: str,
        duplicati_password: str
    ) -> Optional[int]:
        """Verifica si la tarea existe en Duplicati o la crea automáticamente mediante la API REST."""
        session = requests.Session()
        base_url = duplicati_url.rstrip('/')
        managed_job_name = "[CBM] Sistema_Completo"

        if duplicati_password and duplicati_password.strip():
            try:
                self._do_request(
                    session, "POST", f"{base_url}/api/v1/login",
                    password=duplicati_password,
                    json={"password": duplicati_password},
                    timeout=10
                )
            except Exception as e:
                logger.warning(f"⚠️ Login de Duplicati no requerido o fallido: {e}")

        # 1. Buscar si ya existe la tarea en Duplicati
        all_backups = []
        try:
            resp = self._do_request(session, "GET", f"{base_url}/api/v1/backups", password=duplicati_password, timeout=15)
            if resp.status_code == 200:
                all_backups = resp.json()
                if isinstance(all_backups, list):
                    for job in all_backups:
                        job_name = str(job.get("Name", "") or job.get("Backup", {}).get("Name", "")).lower()
                        job_id = int(job.get("ID") or job.get("Backup", {}).get("ID") or 0)
                        if managed_job_name.lower() in job_name or "sistema" in job_name or "cbm" in job_name:
                            logger.info(f"🔎 Tarea encontrada en Duplicati: '{job_name}' (ID: {job_id})")
                            return job_id
        except Exception as e:
            logger.warning(f"⚠️ Error al consultar tareas en Duplicati: {e}")

        # 2. Crear la tarea en Duplicati si no existe
        disaster_recovery_target = os.path.join(target_disk_path.rstrip('/'), "DisasterRecovery")
        try:
            os.makedirs(disaster_recovery_target, exist_ok=True)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo crear el directorio de destino local: {e}")

        clean_path = disaster_recovery_target.replace("file://", "").lstrip('/')
        target_url_encoded = f"file:///{urllib.parse.quote(clean_path, safe='/')}/"

        backup_body = {
            "Name": managed_job_name,
            "Description": "Copia Incremental del Sistema",
            "TargetURL": target_url_encoded,
            "Sources": [source_path],
            "Settings": [
                {"Name": "no-encryption", "Value": "true"},
                {"Name": "compression-module", "Value": "zip"},
                {"Name": "dblock-size", "Value": "50mb"}
            ],
            "Filters": [],
            "Metadata": {}
        }

        for payload in [backup_body, {"Backup": backup_body, "Schedule": None}]:
            try:
                create_resp = self._do_request(
                    session, "POST", f"{base_url}/api/v1/backups",
                    password=duplicati_password,
                    json=payload,
                    timeout=20
                )
                if create_resp.status_code in (200, 201):
                    res_data = create_resp.json()
                    job_id = None
                    if isinstance(res_data, dict):
                        job_id = res_data.get("ID") or res_data.get("id") or (
                            res_data.get("Backup", {}).get("ID") if isinstance(res_data.get("Backup"), dict) else None
                        )
                    if job_id:
                        logger.info(f"✅ Tarea auto-creada en Duplicati con ID: {job_id}")
                        return int(job_id)
            except Exception as e:
                logger.warning(f"⚠️ Intento de creación de tarea fallido: {e}")

        if isinstance(all_backups, list) and len(all_backups) > 0:
            first_id = int(all_backups[0].get("ID") or all_backups[0].get("Backup", {}).get("ID") or 1)
            return first_id

        return None

    def find_job_id_by_name(
        self,
        app_name: str,
        duplicati_url: str = DEFAULT_DUPLICATI_URL,
        duplicati_password: str = DEFAULT_DUPLICATI_PASS
    ) -> Optional[int]:
        try:
            session = requests.Session()
            resp = self._do_request(
                session, "GET", f"{duplicati_url.rstrip('/')}/api/v1/backups",
                password=duplicati_password, timeout=15
            )
            if resp.status_code == 200:
                backups = resp.json()
                if isinstance(backups, list) and len(backups) > 0:
                    target_name = app_name.lower().replace("_", " ").strip()
                    for job in backups:
                        job_name = str(job.get("Name", "") or job.get("Backup", {}).get("Name", "")).lower().replace("_", " ").strip()
                        if target_name in job_name or job_name in target_name:
                            return int(job.get("ID") or job.get("Backup", {}).get("ID"))
                    return int(backups[0].get("ID") or backups[0].get("Backup", {}).get("ID") or 1)
        except Exception as e:
            logger.warning(f"⚠️ Excepción buscando Job ID: {e}")
        return None

    def _run_incremental_rsync_fallback(self, app_name: str, app_path: str, target_disk_path: str) -> Dict[str, Any]:
        """Sincronización incremental como respaldo ligero sin saturar CPU."""
        try:
            out_dir = os.path.join(target_disk_path.rstrip('/'), "DisasterRecovery", f"incremental_{app_name}")
            os.makedirs(out_dir, exist_ok=True)
            cmd = ["rsync", "-av", "--delete", f"{app_path.rstrip('/')}/", f"{out_dir}/"]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return {
                "success": True,
                "job_id": 999,
                "execution_reference": out_dir,
                "metadata": {"mode": "native_incremental_rsync", "destination": out_dir}
            }
        except Exception as e:
            logger.error(f"❌ Error en rsync incremental: {e}")
            return {"success": False, "error": str(e)}

    def run_app_backup(
        self,
        app_name: str,
        app_path: str,
        target_disk_path: str,
        duplicati_job_id: Optional[int] = None,
        duplicati_url: Optional[str] = None,
        duplicati_password: Optional[str] = None
    ) -> Dict[str, Any]:
        cfg_url, cfg_pass = get_duplicati_credentials()
        resolved_url = duplicati_url or cfg_url
        resolved_pass = duplicati_password if duplicati_password is not None else cfg_pass

        is_ok, msg = preflight_service.check_disk_space(
            target_path=target_disk_path,
            required_bytes_estimate=2 * 1024 * 1024 * 1024,
            safety_margin_gb=10.0
        )
        if not is_ok:
            return {"success": False, "error": msg}

        if duplicati_job_id is None:
            duplicati_job_id = self.find_job_id_by_name(app_name, resolved_url, resolved_pass)

        if duplicati_job_id is None:
            return self._run_incremental_rsync_fallback(app_name, app_path, target_disk_path)

        try:
            db_hook_service.create_db_dump(app_name=app_name, app_path=app_path)
            request = BackupExecutionRequest(
                backend_name="duplicati",
                operation=BackupOperationType.RUN_BACKUP,
                manifest=SimpleNamespace(application=app_name),
                backend_configuration=BackendConfiguration(
                    backend_name="duplicati",
                    configuration={"url": resolved_url, "password": resolved_pass, "timeout": 60}
                ),
                backup_configuration=BackupConfiguration(options={"backup_id": duplicati_job_id})
            )
            result = self.backend.execute(request)
            if not result.success:
                return self._run_incremental_rsync_fallback(app_name, app_path, target_disk_path)

            return {
                "success": True,
                "job_id": duplicati_job_id,
                "execution_reference": str(result.execution_reference)
            }
        except Exception as e:
            return self._run_incremental_rsync_fallback(app_name, app_path, target_disk_path)
        finally:
            db_hook_service.cleanup_db_dump(app_path=app_path)

    def run_full_disaster_recovery(
        self,
        app_name: str = "Sistema_Completo",
        app_path: str = "/DATA",
        target_disk_path: Optional[str] = None,
        target_disk: Optional[str] = None,
        duplicati_job_id: Optional[int] = None,
        duplicati_url: Optional[str] = None,
        duplicati_password: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        cfg_url, cfg_pass = get_duplicati_credentials()
        resolved_url = duplicati_url or cfg_url
        resolved_pass = password if password is not None else (duplicati_password or cfg_pass)

        resolved_target = target_disk_path or target_disk
        if not resolved_target or resolved_target == "/var/lib/casaos":
            resolved_target = get_active_target_disk()

        if duplicati_job_id is None:
            duplicati_job_id = self._get_or_create_disaster_recovery_job(
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

    def get_task_status(
        self,
        task_id: Any = 1,
        duplicati_url: Optional[str] = None,
        duplicati_password: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            cfg_url, cfg_pass = get_duplicati_credentials()
            resolved_url = duplicati_url or cfg_url
            resolved_pass = password if password is not None else (duplicati_password or cfg_pass)

            session = requests.Session()
            resp = self._do_request(
                session, "GET", f"{resolved_url.rstrip('/')}/api/v1/progressstate",
                password=resolved_pass, timeout=15
            )
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

            return {"status": "idle", "phase": f"HTTP {resp.status_code}", "progress": 0.0}
        except Exception as e:
            return {"status": "idle", "phase": "Error", "progress": 0.0}


duplicati_orchestrator = DuplicatiOrchestratorService()
duplicati_service = duplicati_orchestrator