import subprocess
import threading
import os
import logging
from datetime import datetime

logger = logging.getLogger("casaos-backup")

class BorgRestoreService:
    def __init__(self):
        self.status = "IDLE"  # IDLE, RUNNING, COMPLETED, FAILED, CANCELLED
        self.archive_name = ""
        self.processed_files = 0
        self.current_file = ""
        self.start_time = None
        self.end_time = None
        self.error_log = []
        self._process = None
        self._thread = None

    def get_status(self):
        return {
            "status": self.status,
            "archive_name": self.archive_name,
            "processed_files": self.processed_files,
            "current_file": self.current_file,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_log": self.error_log
        }

    def start_dry_run(self, repo_path: str, archive_name: str, passphrase: str = None):
        if self.status == "RUNNING":
            return False, "Ya hay un proceso de simulación o restauración en curso."

        self.status = "RUNNING"
        self.archive_name = archive_name
        self.processed_files = 0
        self.current_file = ""
        self.start_time = datetime.now()
        self.end_time = None
        self.error_log = []

        self._thread = threading.Thread(
            target=self._run_dry_run_thread,
            args=(repo_path, archive_name, passphrase),
            daemon=True
        )
        self._thread.start()
        return True, "Simulación iniciada."

    def _run_dry_run_thread(self, repo_path: str, archive_name: str, passphrase: str = None):
        env = os.environ.copy()
        if passphrase:
            env["BORG_PASSPHRASE"] = passphrase

        # Se utiliza --list en lugar de --json-lines para compatibilidad general con Borg
        cmd = [
            "borg", "extract", "--dry-run", "--list",
            f"{repo_path}::{archive_name}"
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1
            )

            # Lectura en tiempo real de los archivos procesados desde stdout
            for line in self._process.stdout:
                clean_line = line.strip()
                if clean_line:
                    self.processed_files += 1
                    self.current_file = clean_line

            self._process.wait()

            if self._process.returncode == 0:
                self.status = "COMPLETED"
            else:
                stderr_output = self._process.stderr.read()
                self.error_log = stderr_output.strip().split("\n")
                if self.status != "CANCELLED":
                    self.status = "FAILED"

        except Exception as e:
            logger.error(f"Error en Borg dry-run: {e}")
            self.error_log.append(str(e))
            self.status = "FAILED"
        finally:
            self.end_time = datetime.now()

    def cancel(self):
        if self.status == "RUNNING" and self._process:
            self.status = "CANCELLED"
            try:
                self._process.terminate()
            except Exception:
                pass
            return True, "Proceso cancelado."
        return False, "No hay ningún proceso activo para cancelar."

borg_restore_service = BorgRestoreService()