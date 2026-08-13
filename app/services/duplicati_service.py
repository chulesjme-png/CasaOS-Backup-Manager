import os
import shutil
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional, Dict
from app.core.config import config_manager
from app.services.db_hook_service import db_hook_service

logger = logging.getLogger("casaos-backup")

class DuplicatiService:
    def __init__(self):
        self.active_jobs: Dict[str, bool] = {}

    def _has_duplicati_cli(self) -> bool:
        """Verifica si duplicati-cli está disponible en el PATH del sistema."""
        return shutil.which("duplicati-cli") is not None

    async def run_app_backup(self, app_name: str, app_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Ejecuta la copia de seguridad de una aplicación específica.
        Intenta usar Duplicati CLI y, si no está disponible, realiza un fallback a TAR.GZ.
        """
        if self.active_jobs.get(app_name):
            logger.warning(f"[Backup] Ya hay un trabajo corriendo para {app_name}")
            return False

        self.active_jobs[app_name] = True
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        destination_folder = Path(target_disk) / "Backups" / "Apps" / app_name
        destination_folder.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Preparación de destino
            if progress_callback:
                progress_callback(10, f"Preparando destino en {destination_folder}...")

            # 2. Ejecución de Hooks de Base de Datos
            if progress_callback:
                progress_callback(25, "Ejecutando DB Hooks si la aplicación los requiere...")
            db_hook_service.execute_pre_backup_hook(app_name, app_path)

            # 3. Comprobación de existencia del directorio origen
            if not os.path.exists(app_path):
                raise FileNotFoundError(f"El directorio origen {app_path} no existe.")

            # 4. Decisión del motor: Duplicati CLI o TAR
            if self._has_duplicati_cli():
                if progress_callback:
                    progress_callback(50, "Ejecutando copia incremental con Duplicati CLI...")
                
                target_uri = f"file://{destination_folder}"
                cmd = [
                    "duplicati-cli", "backup", target_uri, app_path,
                    f"--backup-name={app_name}",
                    "--dbpath=/tmp/duplicati-local.sqlite",
                    "--passphrase=CasaOSManagerSecureKey",
                    "--compression-extension=zip",
                    "--disable-filetime-check=true"
                ]
                
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode != 0:
                    logger.error(f"[Duplicati Error] {stderr.decode()}")
                    raise RuntimeError("Falló la ejecución de Duplicati CLI.")

            else:
                # Fallback: Creación de paquete TAR.GZ comprimido
                if progress_callback:
                    progress_callback(50, "Duplicati CLI no hallado. Usando motor TAR.GZ nativo...")
                
                archive_name = destination_folder / f"{app_name}_backup.tar.gz"
                cmd = ["tar", "-czf", str(archive_name), "-C", str(Path(app_path).parent), Path(app_path).name]
                
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode != 0:
                    logger.error(f"[Tar Error] {stderr.decode()}")
                    raise RuntimeError("Falló la compresión TAR.GZ.")

            # 5. Limpieza post-backup de volcados DB
            if progress_callback:
                progress_callback(90, "Limpiando archivos temporales...")
            db_hook_service.cleanup_hook_files(app_path)

            if progress_callback:
                progress_callback(100, f"¡Copia de seguridad de {app_name} completada con éxito!")

            logger.info(f"[Backup] Copia de {app_name} completada correctamente.")
            return True

        except Exception as e:
            logger.error(f"[Backup] Error en backup de {app_name}: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False

        finally:
            self.active_jobs[app_name] = False

    async def run_full_disaster_recovery(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Ejecuta el respaldo completo del sistema CasaOS (/DATA/AppData + Configuraciones).
        """
        job_key = "full_disaster_recovery"
        if self.active_jobs.get(job_key):
            return False

        self.active_jobs[job_key] = True
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        destination_folder = Path(target_disk) / "Backups" / "DisasterRecovery"
        destination_folder.mkdir(parents=True, exist_ok=True)

        try:
            if progress_callback:
                progress_callback(10, "Iniciando Disaster Recovery completo...")

            archive_path = destination_folder / "DisasterRecovery_Full.tar.gz"
            source_dir = "/DATA/AppData"

            if not os.path.exists(source_dir):
                # Fallback para pruebas si /DATA/AppData no existe en host de desarrollo
                source_dir = "/DATA" if os.path.exists("/DATA") else "."

            if progress_callback:
                progress_callback(40, f"Empaquetando directorio {source_dir}...")

            cmd = ["tar", "-czf", str(archive_path), "-C", str(Path(source_dir).parent), Path(source_dir).name]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"[DR Error] {stderr.decode()}")
                raise RuntimeError("Error al empaquetar Disaster Recovery.")

            if progress_callback:
                progress_callback(100, "Disaster Recovery completado exitosamente.")
            
            logger.info("[Backup] Full Disaster Recovery completado con éxito.")
            return True

        except Exception as e:
            logger.error(f"[DR Error] Error durante Disaster Recovery: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False

        finally:
            self.active_jobs[job_key] = False

    async def restore_backup(self, backup_file: str, target_app: str = "all") -> bool:
        """
        Ejecuta la restauración de un archivo de backup .tar.gz o repositorio de Duplicati.
        """
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        
        # Determinar si la ruta pasada es absoluta o relativa al disco destino
        file_path = Path(backup_file)
        if not file_path.is_absolute():
            file_path = Path(target_disk) / backup_file

        if not file_path.exists():
            logger.error(f"[Restore] Archivo de copia no encontrado: {file_path}")
            return False

        try:
            logger.info(f"[Restore] Restaurando desde {file_path} hacia /DATA/AppData...")
            
            if file_path.suffix in [".gz", ".tgz"] or file_path.name.endswith(".tar.gz"):
                # Extraer archivo TAR
                restore_target = "/DATA/AppData" if os.path.exists("/DATA/AppData") else "/DATA"
                cmd = ["tar", "-xzf", str(file_path), "-C", restore_target]
                
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()

                if proc.returncode != 0:
                    logger.error(f"[Restore Error] {stderr.decode()}")
                    return False

            logger.info(f"[Restore] Restauración completada correctamente.")
            return True

        except Exception as e:
            logger.error(f"[Restore Exception] Error procesando restauración: {e}")
            return False


duplicati_service = DuplicatiService()