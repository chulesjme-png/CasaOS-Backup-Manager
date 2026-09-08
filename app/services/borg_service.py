import asyncio
import re
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class BorgBackupManager:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.process = None

    async def run_backup(self, archive_name: str, source_path: str, progress_callback=None):
        """
        Ejecuta el respaldo de Borg, procesando la salida en tiempo real.
        """
        target_archive = f"{self.repo_path}::{archive_name}"
        cmd = [
            "borg", "create",
            "--progress",
            "--filter", "AME",
            "--stats",
            target_archive,
            source_path
        ]

        logging.info(f"Iniciando respaldo: {' '.join(cmd)}")

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Escuchar la salida stderr para extraer el progreso (\r)
            await self._read_stderr_progress(self.process.stderr, progress_callback)
            
            await self.process.wait()

            if self.process.returncode == 0:
                logging.info("Copia de seguridad completada con éxito.")
                return True
            else:
                logging.error(f"Borg finalizó con código de error: {self.process.returncode}")
                return False

        except asyncio.CancelledError:
            logging.warning("Se ha recibido una solicitud de cancelación de la tarea.")
            await self._handle_cancellation()
            raise

        except Exception as e:
            logging.error(f"Error inesperado durante la ejecución: {e}")
            await self._handle_cancellation()
            return False

    async def _read_stderr_progress(self, stderr_stream, progress_callback):
        """
        Lee el flujo stderr carácter por carácter para detectar '\r' y capturar
        las actualizaciones de progreso de Borg correctamente.
        """
        buffer = ""
        # Expresión regular para capturar patrones de porcentaje en la salida de Borg
        # Ejemplo de salida de Borg: "2.54 GB O 1.20 GB C 15.40 MB A 12300 N ... 45%"
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
                        progress_callback(None, line)
                buffer = ""
            else:
                buffer += char

    async def _handle_cancellation(self):
        """
        Maneja el cierre del proceso y la limpieza del repositorio si el usuario cancela.
        """
        logging.info("Iniciando secuencia de limpieza por cancelación...")

        # 1. Matar el proceso principal si sigue activo
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.sleep(1)
                if self.process.returncode is None:
                    self.process.kill()
                logging.info("Proceso Borg detenido.")
            except Exception as e:
                logging.error(f"Error deteniendo el proceso Borg: {e}")

        # 2. Romper el archivo de bloqueo quedado huérfano (lock.exclusive)
        await self._run_command(["borg", "break-lock", self.repo_path], "Liberando bloqueo del repositorio")

        # 3. Eliminar chunks huérfanos dejados por el intento cancelado
        await self._run_command(["borg", "compact", self.repo_path], "Compactando y eliminando datos no enlazados")

        logging.info("Limpieza completada. El repositorio está listo y limpio para la siguiente copia.")

    async def _run_command(self, cmd: list, description: str):
        """Ejecuta comandos auxiliares de mantenimiento."""
        logging.info(f"{description}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            logging.info(f"Éxito: {description}")
        else:
            logging.error(f"Fallo en {description}: {stderr.decode()}")


# --- EJEMPLO DE USO / PRUEBA DE CANCELACIÓN ---

def update_ui_progress(percent, raw_text):
    if percent is not None:
        print(f"\r[PROGRESO UI] -> {percent}% completo", end="", flush=True)

async def main():
    repo = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa/Backups/DisasterRecovery/BorgRepo"
    source = "/home/pichules/Documentos"
    archive_name = "Copia_Prueba"

    manager = BorgBackupManager(repo_path=repo)

    # Crear una tarea asíncrona para simular la ejecución
    task = asyncio.create_task(manager.run_backup(archive_name, source, update_ui_progress))

    # Simular una cancelación por parte del usuario tras 5 segundos
    await asyncio.sleep(5)
    print("\n\n[USUARIO] Cancelando el proceso de copia...")
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("\nLa tarea fue cancelada correctamente y el repositorio quedó limpio.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass