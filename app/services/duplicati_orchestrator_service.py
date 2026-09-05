import os
import json
import logging
import urllib.parse
import requests
import tarfile
import datetime
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

    def _do_request(
        self,
        session: requests.Session,
        method: str,
        url: str,
        password: str = "",
        **kwargs
    ) -> requests.Response:
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

        all_backups = []
        try:
            resp = self._do_request(session, "GET", f"{base_url}/api/v1/backups", password=duplicati_password, timeout=15)
            if resp.status_code == 200:
                all_backups = resp.json()
                if isinstance(all_backups, list) and len(all_backups) > 0:
                    for job in all_backups:
                        job_name = str(job.get("Name", "") or job.get("Backup", {}).get("Name", "")).lower()
                        job_id = int(job.get("ID") or job.get("Backup", {}).get("ID") or 0)
                        if managed_job_name.lower() in job_name or any(k in job_name for k in ["sistema", "completo", "cbm", "disaster"]):
                            logger.info(f"🔎 Encontrada tarea de sistema '{job_name}' (ID: {job_id})")
                            return job_id
        except Exception as e:
            logger.warning(f"⚠️ Error consultando tareas en Duplicati: {e}")

        disaster_recovery_target = os.path.join(target_disk_path.rstrip('/'), "DisasterRecovery")
        try:
            os.makedirs(disaster_recovery_target, exist_ok=True)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo crear el directorio de destino localmente: {e}")

        clean_path = disaster_recovery_target.replace("file://", "").lstrip('/')
        target_url_encoded = f"file:///{urllib.parse.quote(clean_path, safe='/')}/"

        logger.info(f"🔨 Auto-creando tarea '[CBM] Sistema_Completo' en Duplicati -> {target_url_encoded}")

        payloads = [
            {
                "Backup": {
                    "Name": managed_job_name,
                    "Description": "Copia de Seguridad Completa del Sistema (CasaOS Backup Manager)",
                    "TargetURL": target_url_encoded,
                    "Sources": [source_path],
                    "Settings": [
                        {"Name": "no-encryption", "Value": "true", "Filter": ""},
                        {"Name": "compression-module", "Value": "zip", "Filter": ""},
                        {"Name": "dblock-size", "Value": "50mb", "Filter": ""}
                    ],
                    "Filters": [],
                    "Metadata": {}
                },
                "Schedule": None
            },
            {
                "Backup": {
                    "Name": managed_job_name,
                    "TargetURL": target_url_encoded,
                    "Sources": [source_path],
                    "Settings": [
                        {"Name": "no-encryption", "Value": "true"}
                    ]
                }
            }
        ]

        for idx, payload in enumerate(payloads, start=1):
            try:
                create_resp = self._do_request(
                    session, "POST", f"{base_url}/api/v1/backups",
                    password=duplicati_password,
                    json=payload,
                    timeout=20
                )

                if create_resp.status_code in (200, 201):
                    try:
                        new_job = create_resp.json()
                        if isinstance(new_job, dict):
                            job_id = new_job.get("ID") or new_job.get("id") or (
                                new_job.get("Backup", {}).get("ID") if isinstance(new_job.get("Backup"), dict) else None
                            )
                            if job_id:
                                logger.info(f"✅ Tarea auto-creada en Duplicati con éxito (ID: {job_id})")
                                return int(job_id)
                    except Exception:
                        pass

                    check_resp = self._do_request(session, "GET", f"{base_url}/api/v1/backups", password=duplicati_password, timeout=15)
                    if check_resp.status_code == 200:
                        for job in check_resp.json():
                            name = str(job.get("Name") or job.get("Backup", {}).get("Name", ""))
                            if managed_job_name.lower() in name.lower():
                                job_id = int(job.get("ID") or job.get("Backup", {}).get("ID"))
                                logger.info(f"✅ Tarea auto-creada verificada en Duplicati (ID: {job_id})")
                                return job_id

                logger.warning(f"⚠️ Intento {idx} de auto-creación falló (HTTP {create_resp.status_code}): {create_resp.text}")
            except Exception as e:
                logger.warning(f"⚠️ Excepción en intento {idx} de creación en Duplicati: {e}")

        if isinstance(all_backups, list) and len(all_backups) > 0:
            first_id = int(all_backups[0].get("ID") or all_backups[0].get("Backup", {}).get("ID") or 1)
            logger.info(f"🔎 Usando tarea existente en Duplicati como fallback (ID: {first_id})")
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

    def _run_native_tar_backup(self, app_name: str, app_path: str, target_disk_path: str) -> Dict[str, Any]:
        """Ejecución nativa directa de respaldo (.tar.gz) cuando Duplicati no esté disponible."""
        try:
            out_dir = os.path.join(target_disk_path.rstrip('/'), "DisasterRecovery")
            os.makedirs(out_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backup_{app_name}_{timestamp}.tar.gz"
            filepath = os.path.join(out_dir, filename)

            logger.info(f"📦 Generando copia nativa en: {filepath}")
            with tarfile.open(filepath, "w:gz") as tar:
                if os.path.exists(app_path):
                    tar.add(app_path, arcname=os.path.basename(app_path))

            logger.info(f"✅ Copia de seguridad nativa completada con éxito: {filepath}")
            return {
                "success": True,
                "job_id": 999,
                "execution_reference": filepath,
                "metadata": {"mode": "native_tar", "file": filepath}
            }
        except Exception as e:
            logger.error(f"❌ Error en respaldo nativo: {e}")
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
            duplicati_job_id = self.find_job_id_by_name(app_name, resolved_url, resolved_pass)

        if duplicati_job_id is None:
            logger.warning(f"⚠️ Sin ID en Duplicati para '{app_name}'. Iniciando respaldo nativo...")
            return self._run_native_tar_backup(app_name, app_path, target_disk_path)

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
                        "url": resolved_url,
                        "password": resolved_pass,
                        "timeout": 60
                    }
                ),
                backup_configuration=BackupConfiguration(
                    options={"backup_id": duplicati_job_id}
                )
            )

            result = self.backend.execute(request)
            if not result.success:
                logger.warning("⚠️ Duplicati no pudo procesar la tarea, realizando respaldo nativo...")
                return self._run_native_tar_backup(app_name, app_path, target_disk_path)

            return {
                "success": True,
                "job_id": duplicati_job_id,
                "execution_reference": result.execution_reference.dict() if hasattr(result.execution_reference, "dict") else str(result.execution_reference),
                "metadata": getattr(result, "metadata", {})
            }

        except Exception as e:
            logger.error(f"❌ Excepción en Duplicati: {e}. Ejecutando respaldo nativo de seguridad...")
            return self._run_native_tar_backup(app_name, app_path, target_disk_path)

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
        task_id: int = 1,
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

            return {"status": "error", "phase": f"HTTP {resp.status_code}", "progress": 0.0}
        except Exception as e:
            logger.error(f"⚠️ Error consultando API Duplicati: {e}")
            return {"status": "unknown", "phase": "Error", "progress": 0.0}

duplicati_orchestrator = DuplicatiOrchestratorService()