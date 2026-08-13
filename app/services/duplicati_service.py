import os
import shutil
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from app.core.config import config_manager
from app.core.ws_manager import ws_manager
from app.services.db_hook_service import db_hook_service
from app.services.audit_service import audit_service

logger = logging.getLogger("casaos-backup")

class DuplicatiService:
    def __init__(self):
        self.active_jobs: Dict[str, bool] = {}

    def _has_duplicati_cli(self) -> bool:
        return shutil.which("duplicati-cli") is not None

    async def _notify(self, job_id: str, percentage: int, message: str):
        logger.info(f"[{job_id}] [{percentage}%] {message}")
        await ws_manager.broadcast_progress(job_id, percentage, message)

    async def run_app_backup(self, app_name: str, app_path: str) -> bool:
        job_id = f"backup_{app_name}"
        start_time = time.time()

        if self.active_jobs.get(app_name):
            await self._notify(job_id, 0, f"Ya hay un trabajo corriendo para {app_name}")
            return False

        self.active_jobs[app_name] = True
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        destination_folder = Path(target_disk) / "Backups" / "Apps" / app_name
        destination_folder.mkdir(parents=True, exist_ok=True)

        try:
            await self._notify(job_id, 10, f"Preparando destino en {destination_folder}...")
            await asyncio.sleep(0.2)

            await self._notify(job_id, 25, "Ejecutando DB Hooks si la aplicación los requiere...")
            db_hook_service.execute_pre_backup_hook(app_name, app_path)

            if not os.path.exists(app_path):
                raise FileNotFoundError(f"El directorio origen {app_path} no existe.")

            if self._has_duplicati_cli():
                await self._notify(job_id, 50, "Ejecutando copia incremental con Duplicati CLI...")
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
                await proc.communicate()
            else:
                await self._notify(job_id, 50, "Creando paquete comprimido TAR.GZ...")
                archive_name = destination_folder / f"{app_name}_backup.tar.gz"
                cmd = ["tar", "-czf", str(archive_name), "-C", str(Path(app_path).parent), Path(app_path).name]
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()

            await self._notify(job_id, 90, "Limpiando archivos temporales...")
            db_hook_service.cleanup_hook_files(app_path)

            duration = time.time() - start_time
            await self._notify(job_id, 100, f"¡Copia de seguridad de {app_name} completada con éxito!")
            
            audit_service.log_execution("backup", app_name, "success", duration, "Copia realizada correctamente.")
            return True

        except Exception as e:
            duration = time.time() - start_time
            await self._notify(job_id, 0, f"Error: {str(e)}")
            audit_service.log_execution("backup", app_name, "failed", duration, str(e))
            return False

        finally:
            self.active_jobs[app_name] = False

    async def run_full_disaster_recovery(self) -> bool:
        job_id = "backup_disaster_recovery"
        start_time = time.time()

        if self.active_jobs.get("full_disaster_recovery"):
            return False

        self.active_jobs["full_disaster_recovery"] = True
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        destination_folder = Path(target_disk) / "Backups" / "DisasterRecovery"
        destination_folder.mkdir(parents=True, exist_ok=True)

        try:
            await self._notify(job_id, 10, "Iniciando Disaster Recovery completo...")
            archive_path = destination_folder / "DisasterRecovery_Full.tar.gz"
            source_dir = "/DATA/AppData" if os.path.exists("/DATA/AppData") else "/DATA"

            await self._notify(job_id, 30, f"Empaquetando directorio {source_dir}...")
            cmd = ["tar", "-czf", str(archive_path), "-C", str(Path(source_dir).parent), Path(source_dir).name]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            duration = time.time() - start_time
            await self._notify(job_id, 100, "¡Disaster Recovery completado exitosamente!")
            
            audit_service.log_execution("backup", "Disaster Recovery Full", "success", duration, "Respaldo completo de sistema realizado.")
            return True

        except Exception as e:
            duration = time.time() - start_time
            await self._notify(job_id, 0, f"Error: {str(e)}")
            audit_service.log_execution("backup", "Disaster Recovery Full", "failed", duration, str(e))
            return False

        finally:
            self.active_jobs["full_disaster_recovery"] = False

    async def restore_backup(self, backup_file: str, target_app: str = "all") -> bool:
        job_id = f"restore_{target_app}"
        start_time = time.time()
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        
        file_path = Path(backup_file)
        if not file_path.is_absolute():
            file_path = Path(target_disk) / backup_file

        if not file_path.exists():
            await self._notify(job_id, 0, f"Archivo de copia no encontrado: {file_path}")
            audit_service.log_execution("restore", target_app, "failed", 0, "Archivo no encontrado.")
            return False

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_dir = Path(target_disk) / "Backups" / "Snapshots"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            target_dir = Path("/DATA/AppData") / target_app if (target_app != "all" and target_app) else Path("/DATA/AppData")

            if target_dir.exists():
                snapshot_file = snapshot_dir / f"pre_restore_{target_app}_{timestamp}.tar.gz"
                await self._notify(job_id, 20, f"Creando Snapshot de seguridad previo...")
                
                snap_cmd = ["tar", "-czf", str(snapshot_file), "-C", str(target_dir.parent), target_dir.name]
                proc_snap = await asyncio.create_subprocess_exec(
                    *snap_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc_snap.communicate()

            await self._notify(job_id, 60, f"Restaurando datos desde copia de seguridad...")
            restore_target = "/DATA/AppData" if os.path.exists("/DATA/AppData") else "/DATA"
            cmd = ["tar", "-xzf", str(file_path), "-C", restore_target]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            duration = time.time() - start_time
            await self._notify(job_id, 100, f"¡Restauración completada con éxito!")
            
            audit_service.log_execution("restore", target_app, "success", duration, f"Restaurado desde {backup_file}")
            return True

        except Exception as e:
            duration = time.time() - start_time
            await self._notify(job_id, 0, f"Error durante la restauración: {str(e)}")
            audit_service.log_execution("restore", target_app, "failed", duration, str(e))
            return False

duplicati_service = DuplicatiService()