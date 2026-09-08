import asyncio
import re
import logging
import os
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class BorgService:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.process: Optional[asyncio.subprocess.Process] = None

    async def _run_command(self, cmd: list[str]) -> tuple[int, str, str]:
        """Ejecuta un comando del sistema de forma asíncrona y captura su salida."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode, stdout.decode(errors='ignore'), stderr.decode(errors='ignore')

    async def break_lock(self) -> bool:
        """Fuerza la liberación de cualquier candado huérfano en el repositorio."""
        logger.info(f"Liberando bloqueo del repositorio: {self.repo_path}")
        code, out, err = await self._run_command(["borg", "break-lock", self.repo_path])
        if code == 0:
            logger.info("Bloqueo del repositorio liberado correctamente.")
            return True
        logger.warning(f"Resultado al intentar liberar bloqueo: {err.strip()}")
        return False

    async def compact_repo(self) -> bool:
        """Elimina bloques huérfanos y libera espacio en disco tras errores o cancelaciones."""
        logger.info(f"Compactando repositorio para eliminar residuos: {self.repo_path}")
        code, out, err = await self._run_command(["borg", "compact", self.repo_path])
        if code == 0:
            logger.info("Repositorio compactado y liberado exitosamente.")
            return True
        logger.error(f"Error al compactar el repositorio: {err.strip()}")
        return False

    async def run_backup(
        self,
        archive_name: str,
        source_path: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Ejecuta el respaldo Borg, libera bloqueos previos automáticamente y parsea
        el progreso en tiempo real manejando los caracteres de retorno de carro (\r).
        """
        # Limpieza preventiva de bloqueos huérfanos de ejecuciones previas
        await self.break_lock()

        target_archive = f"{self.repo_path}::{archive_name}"
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
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Monitoreo en tiempo real procesando los retornos de carro '\r'
            await self._read_stderr_progress(self.process.stderr, progress_callback)
            
            await self.process.wait()

            if self.process.returncode == 0:
                logger.info("Respaldo completado exitosamente.")
                return True
            else:
                logger.error(f"Error durante el respaldo Borg (código {self.process.returncode})")
                await self._cleanup_after_failure()
                return False

        except asyncio.CancelledError:
            logger.warning("Solicitud de cancelación recibida durante el respaldo.")
            await self._cleanup_after_cancellation()
            raise

        except Exception as e:
            logger.error(f"Excepción inesperada durante el respaldo: {e}")
            await self._cleanup_after_failure()
            return False
        finally:
            self.process = None

    async def _read_stderr_progress(
        self,
        stderr_stream: asyncio.StreamReader,
        progress_callback: Optional[Callable[[int, str], None]]
    ):
        """
        Lee el flujo stderr byte a byte para capturar '\r' y actualizar la barra
        de progreso en el frontend de forma fluida.
        """
        buffer = ""
        percent_regex = re.compile(r'(\d+)%')

        while True:
            chunk = await stderr_stream.read(1)
            if not chunk:
                break

            char = chunk.decode('utf-8', errors='ignore')

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

    async def _cleanup_after_cancellation(self):
        """Detiene el proceso y ejecuta la rutina de limpieza completa tras cancelar."""
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.sleep(0.5)
                if self.process.returncode is None:
                    self.process.kill()
                logger.info("Proceso Borg finalizado por cancelación.")
            except Exception as e:
                logger.error(f"Error al detener el proceso Borg: {e}")

        await self.break_lock()
        await self.compact_repo()

    async def _cleanup_after_failure(self):
        """Limpia bloqueos si Borg termina con un código de error."""
        await self.break_lock()