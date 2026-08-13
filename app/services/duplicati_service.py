import os
import tarfile
import logging
import asyncio
import docker
from datetime import datetime
from typing import Optional, List, Dict, Any

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
        """Notifica el progreso mediante WebSockets a la interfaz gráfica."""
        payload = {
            "type": "restore_progress",
            "message": message,
            "percent": percent,
            "status": status
        }
        await ws_manager.broadcast(payload)

    def _find_docker_container(self, app_name: str):
        """Busca un contenedor activo o detenido por nombre."""
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

    def list_backups(self) -> List[Dict[str, Any]]:
        """Escanea el disco configurado y devuelve la lista de copias disponibles."""
        target_disk = config_manager.config.selected_target_disk
        if not target_disk or not os.path.exists(target_disk):
            logger.error(f"Disco de destino no disponible: {target_disk}")
            return []

        backups = []
        try:
            for root, _, files in os.walk(target_disk):
                for file in files:
                    if file.endswith(".tar.gz") or file.endswith(".tgz"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, target_disk)
                        size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2)
                        mtime = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d %H:%M:%S")
                        
                        backups.append({
                            "filename": file,
                            "path": rel_path,
                            "full_path": full_path,
                            "size": f"{size_mb} MB",
                            "date": mtime
                        })
        except Exception as e:
            logger.error(f"Error listando copias en {target_disk}: {e}")
            
        return sorted(backups, key=lambda x: x["date"], reverse=True)

    async def run_app_backup(self, app_name: str, app_path: str) -> bool:
        """Ejecuta copia de seguridad individual para una aplicación."""
        target_disk = config_manager.config.selected_target_disk
        dest_dir = os.path.join(target_disk, "Backups", "Apps", app_name)
        os.makedirs(dest_dir, exist_ok=True)
        
        backup_filename = f"{app_name}_backup.tar.gz"
        backup_path = os.path.join(dest_dir, backup_filename)

        try:
            logger.info(f"Iniciando backup para {app_name} desde {app_path}...")
            with tarfile.open(backup_path, "w:gz") as tar:
                if os.path.exists(app_path):
                    tar.add(app_path, arcname=os.path.basename(app_path))

            logger.info(f"Backup exitoso para {app_name}: {backup_path}")
            audit_service.log_event("BACKUP", app_name, "SUCCESS", f"Guardado en {backup_path}")
            await notification_service.send_notification(
                f"Copia Exitosa: {app_name}",
                f"La copia de seguridad para la aplicación <b>{app_name}</b> se ha completado correctamente."
            )
            return True
        except Exception as e:
            logger.error(f"Error creando backup para {app_name}: {e}")
            audit_service.log_event("BACKUP", app_name, "FAILED", str(e))
            return False

    async def run_full_disaster_recovery(self) -> bool:
        """Ejecuta el respaldo programado Disaster Recovery de todo el sistema."""
        logger.info("Iniciando tarea de Disaster Recovery...")
        target_disk = config_manager.config.selected_target_disk
        dest_dir = os.path.join(target_disk, "Backups", "DisasterRecovery")
        os.makedirs(dest_dir, exist_ok=True)

        backup_filename = f"DisasterRecovery_Full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
        backup_path = os.path.join(dest_dir, backup_filename)

        try:
            appdata_dir = "/DATA/AppData"
            if os.path.exists(appdata_dir):
                with tarfile.open(backup_path, "w:gz") as tar:
                    tar.add(appdata_dir, arcname="AppData")

            logger.info("Disaster Recovery completado con éxito.")
            audit_service.log_event("DISASTER_RECOVERY", "ALL", "SUCCESS", f"Guardado en {backup_path}")
            await notification_service.send_notification(
                "Disaster Recovery Completado",
                "El respaldo completo del sistema se ha ejecutado exitosamente."
            )
            return True
        except Exception as e:
            logger.error(f"Error en Disaster Recovery: {e}")
            audit_service.log_event("DISASTER_RECOVERY", "ALL", "FAILED", str(e))
            return False

    async def restore_backup(self, backup_file: str, target_app: str = "all") -> bool:
        """Ejecuta la restauración automatizada '1-Click'."""
        target_disk = config_manager.config.selected_target_disk
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
            await notification_service.send_notification(
                f"Restauración Completada: {app_name}",
                f"La aplicación <b>{app_name}</b> se ha restaurado correctamente desde la copia de seguridad."
            )
            return True

        except Exception as e:
            err_msg = f"Fallo durante la restauración: {str(e)}"
            logger.error(err_msg)
            await self._broadcast_status(err_msg, 0, "error")
            audit_service.log_event("RESTORE", target_app, "FAILED", str(e))
            return False

duplicati_service = BackupRestoreService()