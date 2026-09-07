import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BorgService:
    def __init__(self):
        self.current_process = None

    def get_repo_path(self, target_disk: str) -> str:
        """Construye la ruta del repositorio en el disco seleccionado."""
        return os.path.join(target_disk, "Backups", "DisasterRecovery", "BorgRepo")

    def init_repository_if_needed(self, repo_path: str):
        """Inicializa el repositorio Borg si aún no existe."""
        os.makedirs(os.path.dirname(repo_path), exist_ok=True)
        if not os.path.exists(os.path.join(repo_path, "config")):
            logger.info(f"Inicializando repositorio Borg sin cifrado en: {repo_path}")
            cmd = ["borg", "init", "--encryption=none", repo_path]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"Error al inicializar el repositorio Borg: {res.stderr}")

    def run_backup(self, target_disk: str, source_dir: str = "/DATA") -> bool:
        """Ejecuta la copia comprimida e incremental mediante Borg."""
        repo_path = self.get_repo_path(target_disk)
        self.init_repository_if_needed(repo_path)

        archive_name = f"Sistema_Completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        full_archive = f"{repo_path}::{archive_name}"

        cmd = [
            "borg", "create",
            "--compression", "zstd,3",
            "--stats",
            full_archive,
            source_dir
        ]

        logger.info(f"Iniciando respaldo Borg: {' '.join(cmd)}")
        self.current_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = self.current_process.communicate()

        ret = self.current_process.returncode
        self.current_process = None

        if ret == 0:
            logger.info(f"Respaldo Borg {archive_name} completado con éxito.")
            return True
        else:
            logger.error(f"Error durante el respaldo Borg: {stderr}")
            return False

    def cancel_backup(self) -> bool:
        """Detiene inmediatamente el proceso activo de Borg."""
        if self.current_process and self.current_process.poll() is None:
            logger.info("Enviando señal de cancelación a BorgBackup...")
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.current_process.kill()
            self.current_process = None
            return True
        return False