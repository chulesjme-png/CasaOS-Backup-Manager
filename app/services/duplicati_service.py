import os
import tarfile
import logging
import asyncio
import docker
from typing import Optional

from app.core.ws_manager import ws_manager
from app.services.notification_service import notification_service
from app.services.audit_service import audit_service
from app.core.config import config_manager

logger = logging.getLogger("casaos-backup")

class BackupRestoreService:
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"No se pudo conectar al cliente Docker local: {e}")
            self.docker_client = None

    async def _broadcast_status(self, message: str, percent: int, status: str = "in_progress"):
        payload = {
            "type": "restore_progress",
            "message": message,
            "percent": percent,
            "status": status
        }
        await ws_manager.broadcast(payload)

    def _find_docker_container(self, app_name: str):
        if not self.docker_client:
            return None
        try:
            containers = self.docker_client.containers.list(all=True)
            for container in containers:
                if container.name == app_name or container.name == f"casaos-{app_name}":
                    return container
        except Exception as e:
            logger.error(f"Error al buscar contenedor {app_name}: {e}")
        return None

    async def restore_backup(self, backup_file: str, target_app: str = "all") -> bool:
        target_disk = config_manager.config.selected_target_disk
        
        # Corregido: os.path.isabs
        full_backup_path = backup_file if os.path.isabs(backup_file) else os.path.join(target_disk, backup_file)

        if not os.path.exists(full_backup_path):
            error_msg = f"Archivo de copia no encontrado: {full_backup_path}"
            logger.error(error_msg)
            await self._broadcast_status(error_msg, 0, "error")
            return False

        try:
            await self._broadcast_status(f"Iniciando restauración de {os.path.basename(backup_file)}...", 10)
            await asyncio.sleep(0.5)

            app_name = target_app if target_app != "all" else os.path.basename(backup_file).split("_")[0]
            target_dir = f"/DATA/AppData/{app_name}"

            container = self._find_docker_container(app_name)
            container_was_running = False

            if container:
                if container.status == "running":
                    container_was_running = True
                    await self._broadcast_status(f"Deteniendo contenedor '{container.name}'...", 30)
                    logger.info(f"Deteniendo contenedor {container.name} para restauración...")
                    container.stop(timeout=15)
                    await asyncio.sleep(1)

            os.makedirs(target_dir, exist_ok=True)

            await self._broadcast_status(f"Restaurando archivos en {target_dir}...", 60)
            logger.info(f"Extrayendo {full_backup_path} en {target_dir}")

            if full_backup_path.endswith(".tar.gz") or full_backup_path.endswith(".tgz"):
                with tarfile.open(full_backup_path, "r:gz") as tar:
                    tar.extractall(path=target_dir)
            else:
                with tarfile.open(full_backup_path, "r:*") as tar:
                    tar.extractall(path=target_dir)

            await self._broadcast_status("Archivos extraídos correctamente.", 80)
            await asyncio.sleep(0.5)

            if container and container_was_running:
                await self._broadcast_status(f"Iniciando contenedor '{container.name}'...", 90)
                logger.info(f"Reactivando contenedor {container.name}...")
                container.start()
                await asyncio.sleep(1)

            success_msg = f"Restauración de '{app_name}' completada con éxito."
            await self._broadcast_status(success_msg, 100, "success")
            logger.info(success_msg)

            audit_service.log_event("RESTORE", app_name, "SUCCESS", f"Restaurado desde {backup_file}")
            return True

        except Exception as e:
            err_msg = f"Fallo durante la restauración: {str(e)}"
            logger.error(err_msg)
            await self._broadcast_status(err_msg, 0, "error")
            audit_service.log_event("RESTORE", target_app, "FAILED", str(e))
            return False

duplicati_service = BackupRestoreService()