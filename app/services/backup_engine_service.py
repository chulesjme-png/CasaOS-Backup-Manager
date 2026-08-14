"""
Servicio principal del Backup Engine.

Orquesta la preparación de backups y la ejecución automatizada 
de restauraciones "1-Click" (parada de contenedor, descompresión, arranque y notificación).
"""

import os
import tarfile
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import docker

from app.models.backup_job import BackupJob
from app.models.backup_manifest import BackupManifest
from app.services.backup_manifest_builder_service import BackupManifestBuilderService
from app.services.notification_service import notification_service
from app.core.ws_manager import ws_manager

logger = logging.getLogger("casaos-backup")


class BackupEngineService:
    """
    Orquestador principal del motor de backup y restauración.
    """

    def __init__(
        self,
        manifest_builder: Optional[BackupManifestBuilderService] = None,
    ):
        self.manifest_builder = (
            manifest_builder
            or BackupManifestBuilderService()
        )
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"[BackupEngineService] No se pudo inicializar cliente Docker: {e}")
            self.docker_client = None

    def prepare(
        self,
        backup_job: BackupJob,
    ) -> BackupManifest:
        """
        Prepara un manifiesto a partir de un BackupJob.
        """
        return self.manifest_builder.build(backup_job)

    async def execute_restore_1click(self, app_name: str, file_path: str, target_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Flujo Automatizado de Restauración 1-Click:
        1. Detener el contenedor objetivo (si existe).
        2. Descomprimir los datos en /DATA/AppData/<app_name> (o ruta configurada).
        3. Volver a arrancar el contenedor.
        4. Notificar progreso vía WebSocket y Telegram.
        """
        if not target_path:
            target_path = f"/DATA/AppData/{app_name}"

        dest_dir = Path(target_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive_path = Path(file_path)

        if not archive_path.exists():
            raise FileNotFoundError(f"El archivo de backup {file_path} no existe.")

        container_obj = None
        was_running = False

        # --- FASE 1: Detención de Contenedor ---
        if self.docker_client:
            try:
                containers = self.docker_client.containers.list(all=True)
                for c in containers:
                    if c.name.lower() == app_name.lower():
                        container_obj = c
                        if c.status == "running":
                            was_running = True
                            logger.info(f"[Restore] Deteniendo contenedor '{app_name}'...")
                            await ws_manager.broadcast_json({
                                "type": "restore_progress",
                                "app": app_name,
                                "status": f"Deteniendo contenedor {app_name}..."
                            })
                            c.stop(timeout=15)
                        break
            except Exception as e:
                logger.error(f"[Restore] Error gestionando contenedor Docker para {app_name}: {e}")

        # --- FASE 2: Descompresión/Restauración ---
        logger.info(f"[Restore] Restaurando archivo {archive_path} en {dest_dir}...")
        await ws_manager.broadcast_json({
            "type": "restore_progress",
            "app": app_name,
            "status": "Descomprimiendo archivos..."
        })

        try:
            if archive_path.suffix == ".gz" or archive_path.name.endswith(".tar.gz"):
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(path=dest_dir)
            elif archive_path.suffix == ".zip":
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(dest_dir)
            else:
                raise ValueError(f"Formato de archivo no soportado: {archive_path.name}")
        except Exception as e:
            logger.error(f"[Restore] Error descomprimiendo backup para {app_name}: {e}")
            # Si falló, intentar rearmar el contenedor si estaba corriendo
            if container_obj and was_running:
                try:
                    container_obj.start()
                except Exception:
                    pass
            raise RuntimeError(f"Error en la extracción de datos: {e}")

        # --- FASE 3: Rearranque de Contenedor ---
        if container_obj and was_running:
            try:
                logger.info(f"[Restore] Reiniciando contenedor '{app_name}'...")
                await ws_manager.broadcast_json({
                    "type": "restore_progress",
                    "app": app_name,
                    "status": f"Iniciando contenedor {app_name}..."
                })
                container_obj.start()
            except Exception as e:
                logger.error(f"[Restore] Error reanudando contenedor {app_name}: {e}")

        # --- FASE 4: Notificación ---
        msg = f"Restauración completada con éxito para '{app_name}' en {dest_dir}"
        logger.info(f"[Restore] {msg}")

        await ws_manager.broadcast_json({
            "type": "restore_complete",
            "app": app_name,
            "status": "COMPLETED",
            "message": msg
        })

        if hasattr(notification_service, "send_telegram"):
            try:
                await notification_service.send_telegram(f"✅ *Restauración Exitosa*\n*App:* `{app_name}`\n*Origen:* `{archive_path.name}`")
            except Exception:
                pass

        return {
            "status": "SUCCESS",
            "app_name": app_name,
            "target_path": str(dest_dir),
            "snapshot_id": archive_path.name
        }


backup_engine_service = BackupEngineService()