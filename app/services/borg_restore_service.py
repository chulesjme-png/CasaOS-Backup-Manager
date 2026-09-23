import subprocess
import threading
import os
import logging
from datetime import datetime

logger = logging.getLogger("casaos-backup")

class BorgRestoreService:
    def __init__(self):
        self.restore_state = {
            "status": "IDLE",  # IDLE, RUNNING, COMPLETED, FAILED, CANCELLED
            "archive_name": "",
            "processed_files": 0,
            "current_file": "",
            "start_time": None,
            "end_time": None,
            "error_log": []
        }
        self._process = None
        self._thread = None

    def run_dry_run_simulation(self, repo_path: str, archive_name: str, passphrase: str = None):
        if self.restore_state["status"] == "RUNNING":
            return False, "Ya hay un proceso de simulación o restauración en curso."

        self.restore_state["status"] = "RUNNING"
        self.restore_state["archive_name"] = archive_name
        self.restore_state["processed_files"] = 0
        self.restore_state["current_file"] = ""
        self.restore_state["start_time"] = datetime.now().isoformat()
        self.restore_state["end_time"] = None
        self.restore_state["error_log"] = []

        self._thread = threading.Thread(
            target=self._run_dry_run_thread,
            args=(repo_path, archive_name, passphrase),
            daemon=True
        )
        self._thread.start()
        return True, "Simulación iniciada."

    def start_dry_run(self, repo_path: str, archive_name: str, passphrase: str = None):
        return self.run_dry_run_simulation(repo_path, archive_name, passphrase)

    def _run_dry_run_thread(self, repo_path: str, archive_name: str, passphrase: str = None):
        env = os.environ.copy()
        env["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"] = "yes"
        env["BORG_RELOCATED_REPO_ACCESS_IS_OK"] = "yes"
        if passphrase:
            env["BORG_PASSPHRASE"] = passphrase

        cmd = [
            "borg", "extract", "--dry-run", "--list",
            f"{repo_path}::{archive_name}"
        ]

        try:
            # stdin=DEVNULL evita bloqueos si Borg solicita confirmación por consola
            # stderr=STDOUT redirige errores al mismo flujo de lectura
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                bufsize=1
            )

            for line in self._process.stdout:
                clean_line = line.strip()
                if clean_line:
                    if clean_line.startswith("Error:") or "Exception" in clean_line or "passphrase" in clean_line.lower():
                        self.restore_state["error_log"].append(clean_line)
                    else:
                        self.restore_state["processed_files"] += 1
                        self.restore_state["current_file"] = clean_line

            self._process.wait()

            if self._process.returncode == 0:
                self.restore_state["status"] = "COMPLETED"
            else:
                if self.restore_state["status"] != "CANCELLED":
                    self.restore_state["status"] = "FAILED"
                    if not self.restore_state["error_log"]:
                        self.restore_state["error_log"].append(f"Proceso finalizado con código de error {self._process.returncode}")

        except Exception as e:
            logger.error(f"Error en Borg dry-run: {e}")
            self.restore_state["error_log"].append(str(e))
            self.restore_state["status"] = "FAILED"
        finally:
            self.restore_state["end_time"] = datetime.now().isoformat()

    def cancel(self):
        if self.restore_state["status"] == "RUNNING" and self._process:
            self.restore_state["status"] = "CANCELLED"
            try:
                self._process.terminate()
            except Exception:
                pass
            return True, "Proceso cancelado."
        return False, "No hay ningún proceso activo para cancelar."

borg_restore_service = BorgRestoreService()