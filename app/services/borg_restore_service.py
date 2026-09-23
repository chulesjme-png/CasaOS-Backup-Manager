import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BorgRestoreService:
    def __init__(self):
        self.active_process: Optional[asyncio.subprocess.Process] = None
        self.restore_state: Dict[str, Any] = {
            "status": "IDLE",  # IDLE, RUNNING, COMPLETED, FAILED, CANCELLED
            "archive_name": None,
            "processed_files": 0,
            "current_file": "",
            "start_time": None,
            "end_time": None,
            "error_log": []
        }

    async def run_dry_run_simulation(self, repo_path: str, archive_name: str, passphrase: Optional[str] = None):
        """Ejecuta una simulación de extracción (Dry-Run) en segundo plano."""
        if self.restore_state["status"] == "RUNNING":
            raise RuntimeError("Ya hay una simulación o restauración en curso.")

        self.restore_state.update({
            "status": "RUNNING",
            "archive_name": archive_name,
            "processed_files": 0,
            "current_file": "",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "error_log": []
        })

        env = {}
        if passphrase:
            env["BORG_PASSPHRASE"] = passphrase

        cmd = [
            "borg", "extract",
            "--dry-run",
            "--list",
            "--json-lines",
            f"{repo_path}::{archive_name}"
        ]

        try:
            self.active_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            # Tareas para consumir logs en tiempo real
            asyncio.create_task(self._consume_stdout())
            asyncio.create_task(self._consume_stderr())

            return_code = await self.active_process.wait()

            self.restore_state["end_time"] = datetime.now().isoformat()
            if return_code == 0:
                self.restore_state["status"] = "COMPLETED"
                logger.info(f"Simulación Dry-Run finalizada con éxito para {archive_name}")
            else:
                self.restore_state["status"] = "FAILED"
                logger.error(f"Simulación Dry-Run falló con código {return_code}")

        except Exception as e:
            self.restore_state["status"] = "FAILED"
            self.restore_state["error_log"].append(str(e))
            logger.exception("Error durante la simulación de restauración")
        finally:
            self.active_process = None

    async def _consume_stdout(self):
        """Parsea la salida JSON de Borg para medir el progreso."""
        if not self.active_process or not self.active_process.stdout:
            return

        while True:
            line = await self.active_process.stdout.readline()
            if not line:
                break
            try:
                data = json.loads(line.decode().strip())
                if data.get("type") == "archive_progress":
                    self.restore_state["processed_files"] += 1
                    self.restore_state["current_file"] = data.get("path", "")
            except json.JSONDecodeError:
                continue

    async def _consume_stderr(self):
        """Captura advertencias o errores reportados por Borg."""
        if not self.active_process or not self.active_process.stderr:
            return

        while True:
            line = await self.active_process.stderr.readline()
            if not line:
                break
            err_line = line.decode().strip()
            if err_line:
                self.restore_state["error_log"].append(err_line)

    def cancel_simulation(self) -> bool:
        """Detiene la simulación en caso de emergencia."""
        if self.active_process and self.restore_state["status"] == "RUNNING":
            self.active_process.terminate()
            self.restore_state["status"] = "CANCELLED"
            self.restore_state["end_time"] = datetime.now().isoformat()
            return True
        return False

# Instancia singleton accesible desde la API
borg_restore_service = BorgRestoreService()