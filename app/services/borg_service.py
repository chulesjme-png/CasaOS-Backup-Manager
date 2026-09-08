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
        try:
            res = subprocess.run(["du", "-sb", path], capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout:
                return int(res.stdout.split()[0])
        except Exception as e:
            logger.warning(f"No se pudo calcular el tamaño total con du: {e}")
        
        total = 0
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    fp = os.path.join(root, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
        except Exception:
            pass
        return total or 1

    def _parse_borg_bytes(self, text: str) -> Optional[int]:
        """Extrae los bytes procesados (Originales) de las líneas de progreso de Borg."""
        match = re.search(r'([\d\.]+)\s*(B|kB|MB|GB|TB|PB)\s+O', text, re.IGNORECASE)
        if not match:
            return None
        
        val = float(match.group(1))
        unit = match.group(2).upper()
        
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4,
            'PB': 1024**5
        }
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
            if res.returncode == 0:
                logger.info("Bloqueo del repositorio liberado correctamente.")
                return True
            logger.warning(f"Resultado al intentar liberar bloqueo: {res.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"Error al ejecutar break-lock: {e}")
            return False

    def compact_repo(self, repo_path: Optional[str] = None) -> bool:
        """Elimina bloques huérfanos y libera espacio físico en disco tras errores o cancelaciones."""
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
            if res.returncode == 0:
                logger.info("Repositorio compactado y espacio liberado exitosamente.")
                return True
            logger.error(f"Error al compactar el repositorio: {res.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"Error al ejecutar compact: {e}")
            return False

    def _cleanup_after_cancellation(self, repo_path: str, archive_name: str = "Sistema_Completo"):
        """Elimina cualquier copia parcial (checkpoint) y libera físicamente el espacio ocupado en disco."""
        logger.info(f"Iniciando limpieza profunda de restos en: {repo_path}")
        
        # 1. Liberar candados
        self.break_lock(repo_path)
        
        # 2. Borrar respaldos parciales y checkpoints
        try:
            logger.info(f"Eliminando respaldos parciales/checkpoints para '{archive_name}'...")
            res = subprocess.run(
                ["borg", "delete", "--glob", f"{archive_name}*", repo_path],
                capture_output=True,
                text=True,
                env=self._get_env()
            )
            if res.returncode == 0:
                logger.info("Respaldos parciales y checkpoints eliminados.")
            else:
                logger.debug(f"Detalle al eliminar checkpoints: {res.stderr.strip()}")
        except Exception as e:
            logger.warning(f"No se pudieron eliminar los checkpoints parciales: {e}")

        # 3. Compactar para purgar bloques huérfanos y recuperar espacio
        self.compact_repo(repo_path)

    def _cleanup_after_failure(self, repo_path: str, archive_name: str = "Sistema_Completo"):
        """Limpia bloqueos y elimina datos corruptos/incompletos tras un fallo."""
        self._cleanup_after_cancellation(repo_path, archive_name)

    def run_backup(
        self,
        repo_path: Optional[str] = None,
        archive_name: str = "Sistema_Completo",
        source_path: str = "/DATA/AppData",
        progress_callback: Optional[Callable[[int, str], None]] = None,
        target_disk: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Ejecuta el respaldo Borg con seguimiento dinámico del progreso y limpieza garantizada al cancelar."""
        self._is_cancelled = False
        raw_path = repo_path or target_disk or kwargs.get("target_disk")
        target_repo = self._resolve_repo_path(raw_path)
        
        if not target_repo:
            logger.error("No se ha proporcionado la ruta del repositorio de Borg.")
            return False

        if not self._ensure_repo_exists(target_repo):
            return False

        self.break_lock(target_repo)

        if not archive_name:
            archive_name = "Sistema_Completo"

        if not source_path:
            source_path = "/DATA/AppData"

        total_bytes = self._get_dir_size(source_path)
        logger.info(f"Tamaño total de {source_path}: {total_bytes / (1024**2):.2f} MB")

        target_archive = f"{target_repo}::{archive_name}"
        cmd = [
            "borg", "create",
            "--progress",
            "--compression", "zstd,3",
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

            self.process.wait()

            if self._is_cancelled or self.process.returncode != 0:
                if self._is_cancelled:
                    logger.warning("Respaldo cancelado por el usuario.")
                    self._cleanup_after_cancellation(target_repo, archive_name=archive_name)
                else:
                    logger.error(f"Error durante el respaldo Borg (código {self.process.returncode})")
                    self._cleanup_after_failure(target_repo, archive_name=archive_name)
                return False

            if progress_callback:
                progress_callback(100, "Respaldo Borg completado exitosamente.")

            logger.info("Respaldo completado exitosamente.")
            return True

        except Exception as e:
            logger.error(f"Excepción inesperada durante el respaldo: {e}")
            self._cleanup_after_failure(target_repo, archive_name=archive_name)
            return False
        finally:
            try:
                os.close(master_fd)
            except Exception:
                pass
            self.process = None

    def cancel_backup(self, repo_path: Optional[str] = None, archive_name: str = "Sistema_Completo"):
        """Detiene el proceso en curso y elimina cualquier resto del disco."""
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
                logger.info("Proceso Borg finalizado por el usuario.")
            except Exception as e:
                logger.error(f"Error al detener el proceso Borg: {e}")

        target_repo = self._resolve_repo_path(repo_path)
        if target_repo:
            self._cleanup_after_cancellation(target_repo, archive_name=archive_name)