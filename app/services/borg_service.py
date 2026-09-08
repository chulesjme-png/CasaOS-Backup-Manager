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

    def _resolve_repo_path(self, path: Optional[str]) -> Optional[str]:
        """Resuelve la ruta exacta del repositorio de Borg permitiendo rutas de disco o directas."""
        target = path or self.repo_path
        if not target:
            return None
        
        subpath = os.path.join(target, "Backups", "DisasterRecovery", "BorgRepo")
        if os.path.exists(subpath):
            return subpath
            
        return target

    def break_lock(self, repo_path: Optional[str] = None) -> bool:
        """Fuerza la liberación de cualquier candado huérfano en el repositorio."""
        target_repo = self._resolve_repo_path(repo_path)
        if not target_repo:
            logger.error("No se especificó la ruta del repositorio para liberar el bloqueo.")
            return False

        logger.info(f"Liberando bloqueo del repositorio: {target_repo}")
        try:
            res = subprocess.run(["borg", "break-lock", target_repo], capture_output=True, text=True)
            if res.returncode == 0:
                logger.info("Bloqueo del repositorio liberado correctamente.")
                return True
            logger.warning(f"Resultado al intentar liberar bloqueo: {res.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"Error al ejecutar break-lock: {e}")
            return False

    def compact_repo(self, repo_path: Optional[str] = None) -> bool:
        """Elimina bloques huérfanos y libera espacio en disco tras errores o cancelaciones."""
        target_repo = self._resolve_repo_path(repo_path)
        if not target_repo:
            logger.error("No se especificó la ruta del repositorio para compactar.")
            return False

        logger.info(f"Compactando repositorio para eliminar residuos: {target_repo}")
        try:
            res = subprocess.run(["borg", "compact", target_repo], capture_output=True, text=True)
            if res.returncode == 0:
                logger.info("Repositorio compactado y liberado exitosamente.")
                return True
            logger.error(f"Error al compactar el repositorio: {res.stderr.strip()}")
            return False
        except Exception as e:
            logger.error(f"Error al ejecutar compact: {e}")
            return False

    def run_backup(
        self,
        repo_path: Optional[str] = None,
        archive_name: str = "Sistema_Completo",
        source_path: str = "/DATA/AppData",
        progress_callback: Optional[Callable[[int, str], None]] = None,
        target_disk: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Ejecuta el respaldo Borg de forma sincrónica, compatible con trabajadores de fondo.
        """
        self._is_cancelled = False
        raw_path = repo_path or target_disk or kwargs.get("target_disk")
        target_repo = self._resolve_repo_path(raw_path)
        
        if not target_repo:
            logger.error("No se ha proporcionado la ruta del repositorio de Borg.")
            return False

        # Limpieza preventiva de bloqueos previos
        self.break_lock(target_repo)

        if not archive_name:
            archive_name = "Sistema_Completo"

        if not source_path:
            source_path = "/DATA/AppData"

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

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )

            # Lectura en tiempo real byte a byte procesando caracteres '\r'
            percent_regex = re.compile(r'(\d+)%')
            buffer = ""

            while True:
                if self._is_cancelled:
                    break

                char_bytes = self.process.stderr.read(1)
                if not char_bytes:
                    break

                char = char_bytes.decode('utf-8', errors='ignore')

                if char in ['\r', '\n']:
                    line = buffer.strip()
                    if line and progress_callback:
                        match = percent_regex.search(line)
                        if match:
                            percentage = int(match.group(1))
                            progress_callback(percentage, line)
                        else:
                            progress_callback(0, line)
                    buffer = ""
                else:
                    buffer += char

            self.process.wait()

            if self._is_cancelled or self.process.returncode != 0:
                if self._is_cancelled:
                    logger.warning("Respaldo cancelado por el usuario.")
                    self._cleanup_after_cancellation(target_repo)
                else:
                    logger.error(f"Error durante el respaldo Borg (código {self.process.returncode})")
                    self._cleanup_after_failure(target_repo)
                return False

            logger.info("Respaldo completado exitosamente.")
            return True

        except Exception as e:
            logger.error(f"Excepción inesperada durante el respaldo: {e}")
            self._cleanup_after_failure(target_repo)
            return False
        finally:
            self.process = None

    def cancel_backup(self, repo_path: Optional[str] = None):
        """Detiene el proceso en curso y ejecuta la limpieza del repositorio."""
        self._is_cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
                logger.info("Proceso Borg finalizado por cancelación.")
            except Exception as e:
                logger.error(f"Error al detener el proceso Borg: {e}")

        target_repo = self._resolve_repo_path(repo_path)
        if target_repo:
            self._cleanup_after_cancellation(target_repo)

    def _cleanup_after_cancellation(self, repo_path: str):
        """Ejecuta la liberación de candados y compactación tras cancelar."""
        self.break_lock(repo_path)
        self.compact_repo(repo_path)

    def _cleanup_after_failure(self, repo_path: str):
        """Limpia bloqueos tras un error inesperado."""
        self.break_lock(repo_path)