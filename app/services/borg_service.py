import pty
import subprocess
import re
import logging
import os
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class BorgService:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = repo_path
        self.process: Optional[subprocess.Popen] = None
        self._is_cancelled = False

    def _get_env(self) -> dict:
        """Entorno con flags para evitar confirmaciones interactivas de Borg."""
        env = os.environ.copy()
        env["BORG_UNKNOWN_UNENCRYPTED_REPO_ACCESS_IS_OK"] = "yes"
        env["BORG_RELOCATED_REPO_ACCESS_IS_OK"] = "yes"
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def _resolve_repo_path(self, path: Optional[str]) -> Optional[str]:
        """Limpia la ruta recibida y evita la duplicación de carpetas '/Backups'."""
        target = path or self.repo_path
        if not target:
            return None
        
        target = os.path.normpath(target)
        while "/Backups/Backups" in target:
            target = target.replace("/Backups/Backups", "/Backups")

        if target.endswith("BorgRepo"):
            return target
        if target.endswith("DisasterRecovery"):
            return os.path.join(target, "BorgRepo")
        if target.endswith("Backups"):
            return os.path.join(target, "DisasterRecovery", "BorgRepo")

        return os.path.join(target, "Backups", "DisasterRecovery", "BorgRepo")

    def _ensure_repo_exists(self, repo_path: str) -> bool:
        """Crea la estructura de carpetas e inicializa el repositorio Borg si aún no existe."""
        try:
            os.makedirs(repo_path, exist_ok=True)
            config_file = os.path.join(repo_path, "config")
            
            if not os.path.exists(config_file):
                logger.info(f"Inicializando nuevo repositorio Borg en: {repo_path}")
                cmd = ["borg", "init", "--encryption=none", repo_path]
                res = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    env=self._get_env()
                )
                if res.returncode != 0:
                    logger.error(f"Error al inicializar repositorio Borg: {res.stderr.strip()}")
                    return False
                logger.info("Repositorio Borg inicializado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error al verificar/crear el directorio del repositorio: {e}")
            return False

    def _get_dir_size(self, path: str) -> int:
        """Calcula el tamaño total en bytes del directorio de origen."""
        if not os.path.exists(path):
            return 1

        if os.path.isfile(path):
            return os.path.getsize(path)

        try:
            res = subprocess.run(["du", "-sbx", path], capture_output=True, text=True, timeout=90)
            if res.returncode == 0 and res.stdout:
                return int(res.stdout.split()[0])
        except Exception as e:
            logger.warning(f"No se pudo calcular el tamaño total con du: {e}")

        total = 0
        try:
            def scan_dir(dir_path):
                size = 0
                with os.scandir(dir_path) as it:
                    for entry in it:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                size += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                size += scan_dir(entry.path)
                        except Exception:
                            continue
                return size
            total = scan_dir(path)
        except Exception as e:
            logger.warning(f"Error en escaneo de directorio: {e}")

        return total or 1

    def _parse_borg_bytes(self, text: str) -> Optional[int]:
        """Extrae los bytes procesados (Originales) de las líneas de progreso de Borg."""
        match = re.search(r'([\d\.,]+)\s*(B|kB|MB|GB|TB|PB)\s+O', text, re.IGNORECASE)
        if not match:
            return None
        
        val_str = match.group(1).replace(',', '.')
        try:
            val = float(val_str)
        except ValueError:
            return None

        unit = match.group(2).upper()
        units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4, 'PB': 1024**5}
        return int(val * units.get(unit, 1))

    def break_lock(self, repo_path: Optional[str] = None) -> bool:
        """Fuerza la liberación de cualquier candado huérfano en el repositorio."""
        target_repo = self._resolve_repo_path(repo_path)
        if not target_repo or not os.path.exists(os.path.join(target_repo, "config")):
            return False

        logger.info(f"Liberando bloqueo del repositorio: {target_repo}")
        try:
            res = subprocess.run(
                ["borg", "break-lock", target_repo],
                capture_output=True,
                text=True,
                env=self._get_env()
            )
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Error al ejecutar break-lock: {e}")
            return False

    def compact_repo(self, repo_path: Optional[str] = None) -> bool:
        """Elimina bloques huérfanos y libera espacio físico en disco."""
        target_repo = self._resolve_repo_path(repo_path)
        if not target_repo or not os.path.exists(os.path.join(target_repo, "config")):
            return False

        time.sleep(1)
        logger.info(f"Compactando repositorio para liberar espacio físico: {target_repo}")
        try:
            res = subprocess.run(
                ["borg", "compact", target_repo],
                capture_output=True,
                text=True,
                env=self._get_env()
            )
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Error al ejecutar compact: {e}")
            return False

    def _cleanup_after_cancellation(self, repo_path: str, archive_name: str):
        """Elimina ÚNICAMENTE checkpoints parciales incalculados sin afectar backups completados."""
        logger.info(f"Iniciando limpieza de checkpoints temporales en: {repo_path}")
        self.break_lock(repo_path)
        
        try:
            # Se busca únicamente el patrón .checkpoint para proteger el backup real
            checkpoint_pattern = f"{archive_name}*.checkpoint*"
            logger.info(f"Eliminando solo checkpoints incompletos matching: '{checkpoint_pattern}'...")
            subprocess.run(
                ["borg", "delete", "--glob", checkpoint_pattern, repo_path],
                capture_output=True,
                text=True,
                env=self._get_env()
            )
        except Exception as e:
            logger.warning(f"No se pudieron eliminar los checkpoints parciales: {e}")

        self.compact_repo(repo_path)

    def run_backup(
        self,
        repo_path: Optional[str] = None,
        archive_name: str = "Sistema_Completo",
        source_path: str = "/DATA/AppData",
        progress_callback: Optional[Callable[[int, str], None]] = None,
        target_disk: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Ejecuta el respaldo Borg garantizando nombres únicos con marca de tiempo."""
        self._is_cancelled = False
        raw_path = repo_path or target_disk or kwargs.get("target_disk")
        target_repo = self._resolve_repo_path(raw_path)
        
        if not target_repo or not self._ensure_repo_exists(target_repo):
            return False

        self.break_lock(target_repo)

        base_name = archive_name or "Sistema_Completo"
        # Se genera un timestamp para garantizar que no colisionen nombres existentes
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        full_archive_name = f"{base_name}_{timestamp}"

        if not source_path:
            source_path = "/DATA/AppData"

        total_bytes = self._get_dir_size(source_path)
        logger.info(f"Tamaño total de {source_path}: {total_bytes / (1024**2):.2f} MB")

        target_archive = f"{target_repo}::{full_archive_name}"
        cmd = [
            "borg", "create",
            "--progress",
            "--compression", "zstd,3",
            "--exclude", "*/data/*.log",
            "--exclude", "*/cache/*",
            "--stats",
            target_archive,
            source_path
        ]

        logger.info(f"Iniciando respaldo Borg: {' '.join(cmd)}")

        master_fd, slave_fd = pty.openpty()

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=slave_fd,
                close_fds=True,
                env=self._get_env()
            )
            os.close(slave_fd)

            buffer = ""
            current_percent = 10

            while True:
                if self._is_cancelled:
                    if self.process and self.process.poll() is None:
                        self.process.terminate()
                    break

                try:
                    chunk = os.read(master_fd, 256)
                    if not chunk:
                        break
                    
                    text = chunk.decode('utf-8', errors='ignore')
                    for char in text:
                        if char in ['\r', '\n']:
                            line = buffer.strip()
                            if line and progress_callback:
                                processed_bytes = self._parse_borg_bytes(line)
                                if processed_bytes is not None and total_bytes > 0:
                                    calc_pct = 10 + int((processed_bytes / total_bytes) * 85)
                                    current_percent = min(95, max(current_percent, calc_pct))
                                progress_callback(current_percent, line)
                            buffer = ""
                        else:
                            buffer += char
                except OSError:
                    break

            if self.process:
                self.process.wait()

            # Borg utiliza returncode == 1 para advertencias no críticas (e.g. archivos cambiados).
            # Se considera fallo únicamente si fue cancelado o si returncode es mayor a 1.
            if self._is_cancelled or (self.process and self.process.returncode > 1):
                ret_code = self.process.returncode if self.process else -1
                logger.error(f"Error o cancelación durante el respaldo Borg (código {ret_code})")
                self._cleanup_after_cancellation(target_repo, full_archive_name)
                return False

            if progress_callback:
                progress_callback(100, "Respaldo Borg completado exitosamente.")

            logger.info("Respaldo completado exitosamente.")
            return True

        except Exception as e:
            logger.error(f"Excepción inesperada durante el respaldo: {e}")
            if target_repo:
                self._cleanup_after_cancellation(target_repo, full_archive_name)
            return False
        finally:
            try:
                os.close(master_fd)
            except Exception:
                pass
            self.process = None

    def cancel_backup(self, repo_path: Optional[str] = None, archive_name: str = "Sistema_Completo"):
        """Detiene el proceso en curso sin borrar copias previas completadas."""
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception as e:
                logger.error(f"Error al detener el proceso Borg: {e}")

        target_repo = self._resolve_repo_path(repo_path)
        if target_repo:
            self._cleanup_after_cancellation(target_repo, archive_name)