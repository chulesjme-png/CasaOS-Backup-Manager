import logging
import requests
from typing import Dict, Any, Optional

from app.core.backends.base_backend import BaseBackend
from app.models.backup_execution_request import BackupExecutionRequest
from app.models.backup_execution_result import BackupExecutionResult, ExecutionStatus, ExecutionReference

logger = logging.getLogger("casaos-backup")

class DuplicatiBackend(BaseBackend):
    def __init__(self):
        super().__init__(name="duplicati")

    def _get_authenticated_session(self, url: str, password: str) -> requests.Session:
        session = requests.Session()
        base_url = url.rstrip('/')
        
        # Obtener cookies de sesión y token XSRF
        try:
            init_resp = session.get(f"{base_url}/api/v1/backups", timeout=5)
            xsrf_token = session.cookies.get("XSRF-TOKEN")
            if xsrf_token:
                session.headers.update({"X-XSRF-Token": xsrf_token})
            elif password:
                session.headers.update({"X-XSRF-Token": password})
        except Exception as e:
            logger.warning(f"⚠️ No se pudo inicializar sesión con Duplicati: {e}")
            if password:
                session.headers.update({"X-XSRF-Token": password})

        return session

    def execute(self, request: BackupExecutionRequest) -> BackupExecutionResult:
        config = request.backend_configuration.configuration
        url = config.get("url", "http://172.17.0.1:8200").rstrip("/")
        password = config.get("password", "")
        timeout = config.get("timeout", 30)

        backup_options = request.backup_configuration.options or {}
        backup_id = backup_options.get("backup_id", 1)

        session = self._get_authenticated_session(url, password)
        endpoint = f"{url}/api/v1/backup/{backup_id}/start"

        try:
            logger.info(f"📡 Iniciando tarea de respaldo en Duplicati (ID: {backup_id}) en {endpoint}")
            response = session.post(endpoint, timeout=timeout)

            if response.status_code in [200, 202]:
                return BackupExecutionResult(
                    success=True,
                    status=ExecutionStatus.SUCCESS,
                    execution_reference=ExecutionReference(
                        backend_name=self.name,
                        reference_id=str(backup_id)
                    ),
                    metadata={"status_code": response.status_code, "backup_id": backup_id}
                )
            else:
                err_msg = f"Error reportado por Duplicati (HTTP {response.status_code})"
                logger.error(f"❌ Error al iniciar backup en Duplicati: {err_msg} - {response.text}")
                return BackupExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    execution_reference=ExecutionReference(
                        backend_name=self.name,
                        reference_id=str(backup_id)
                    ),
                    errors=[err_msg]
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error de conexión con Duplicati: {e}")
            return BackupExecutionResult(
                success=False,
                status=ExecutionStatus.FAILED,
                execution_reference=ExecutionReference(
                    backend_name=self.name,
                    reference_id=str(backup_id)
                ),
                errors=[f"Error de conexión: {str(e)}"]
            )