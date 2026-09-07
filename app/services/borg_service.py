import os
import re
import signal
import subprocess
import logging
from datetime import datetime
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class BorgService:
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None

    def _get_borg_env(self) -> dict:
        """Inyecta variables de entorno para prevenir bloqueos por solicitudes interactivas en Borg."""
        env = os.environ.copy()
        env["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"] = "yes"
        env["BORG_RELOCATED_REPO_ACCESS_IS_OK"] = "yes"
        env["BORG_UNKNOWN_CLI_OPTION_IS_OK"] = "yes"
        return env

    def get_repo_path(self, target_disk: Optional[str]) -> str:
        """Construye la ruta del repositorio evitando duplicar el directorio 'Backups'."""
        if not target_disk:
            target_disk = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa"

        target_disk = target_disk.rstrip("/")
        if target_disk.endswith("Backups"):
            base_path = target_disk
        else:
            base_path = os.path.join(target_disk, "Backups")

        return os.path.join(base_path, "DisasterRecovery", "BorgRepo")

    def init_repository_if_needed(self, repo_path: str):
        """Inicializa el repositorio Borg si aún no existe."""
        os.makedirs(repo_path, exist_ok=True)
        config_path = os.path.join(repo_path, "config")
        env = self._get_borg_env()

        if not os.path.exists(config_path):
            logger.info(f"Inicializando repositorio Borg sin cifrado en: {repo_path}")
            cmd = ["borg", "init", "--encryption=none", repo_path]
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if res.returncode != 0:
                raise RuntimeError(f"Error al inicializar el repositorio Borg: {res.stderr}")

    def _get_source_size(self, source_dir: str) -> int:
        """Calcula el tamaño total en bytes del directorio origen para calcular el porcentaje."""
        total_bytes = 0
        try:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    try:
                        fp = os.path.join(root, f)
                        if not os.path.islink(fp):
                            total_bytes += os.path.getsize(fp)
                    except OSError:
                        pass
        except Exception as e:
            logger.warning(f"No se pudo calcular el tamaño total de {source_dir}: {e}")
        return total_bytes

    def run_backup(
        self,
        target_disk: Optional[str] = None,
        source_dir: str = "/DATA",
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> bool:
        """Ejecuta la copia comprimida e incremental mediante Borg reportando progreso en tiempo real."""
        repo_path = self.get_repo_path(target_disk)
        self.init_repository_if_needed(repo_path)

        archive_name = f"Sistema_Completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        full_archive = f"{repo_path}::{archive_name}"

        if progress_callback:
            progress_callback(5.0, "Calculando tamaño del sistema a respaldar...")

        total_bytes = self._get_source_size(source_dir)

        cmd = [
            "borg", "create",
            "--progress",
            "--compression", "zstd,3",
            "--stats",
            full_archive,
            source_dir
        ]

        logger.info(f"Iniciando respaldo Borg: {' '.join(cmd)}")
        env = self._get_borg_env()

        self.current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None
        )

        pattern = re.compile(r'(\d+\.\d+|\d+)\s*([KMGT]?B)\s+O')
        multiplier = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}

        last_progress = 10.0
        if progress_callback:
            progress_callback(10.0, "Iniciando transferencia Borg...")

        while True:
            char_list = []
            while True:
                char = self.current_process.stderr.read(1)
                if not char:
                    break
                if char in ['\r', '\n']:
                    break
                char_list.append(char)

            line = "".join(char_list)
            if not line and self.current_process.poll() is not None:
                break

            match = pattern.search(line)
            if match and total_bytes > 0:
                val, unit = match.groups()
                current_bytes = float(val) * multiplier.get(unit.upper(), 1)
                
                pct = 10.0 + (current_bytes / total_bytes) * 85.0
                pct = round(min(pct, 95.0), 1)

                if pct > last_progress:
                    last_progress = pct
                    if progress_callback:
                        progress_callback(pct, f"Procesando copia de seguridad... {pct}%")

        self.current_process.wait()
        ret = self.current_process.returncode
        self.current_process = None

        if ret == 0:
            logger.info(f"Respaldo Borg {archive_name} completado con éxito.")
            if progress_callback:
                progress_callback(100.0, "Respaldo completado con éxito.")
            return True
        else:
            logger.error(f"Error durante el respaldo Borg (código {ret})")
            if progress_callback:
                progress_callback(last_progress, f"Error en respaldo Borg (Código {ret})")
            return False

    def cancel_backup(self) -> bool:
        """Detiene inmediatamente el proceso activo de Borg."""
        if self.current_process and self.current_process.poll() is None:
            logger.info("Enviando señal de cancelación a BorgBackup...")
            try:
                os.killpg(os.getpgid(self.current_process.pid), signal.SIGKILL)
            except Exception:
                self.current_process.kill()
            self.current_process = None
            return True
        return False


borg_service = BorgService()