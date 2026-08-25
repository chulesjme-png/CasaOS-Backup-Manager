import os
import glob
import json
import asyncio
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
    def __init__(
        self,
        manifest_builder: Optional[BackupManifestBuilderService] = None,
    ):
        self.manifest_builder = (
            manifest_builder or BackupManifestBuilderService()
        )
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"[BackupEngineService] No se pudo inicializar cliente Docker: {e}")
            self.docker_client = None

    @staticmethod
    def apply_retention_policy(target_dir: str, prefix: str = "", max_copies: int = 3) -> None:
        try:
            if not target_dir or not os.path.exists(target_dir):
                return

            if prefix:
                pattern_tar = os.path.join(target_dir, f"*{prefix}*.tar.gz")
                pattern_zip = os.path.join(target_dir, f"*{prefix}*.zip")
            else:
                pattern_tar = os.path.join(target_dir, "*.tar.gz")
                pattern_zip = os.path.join(target_dir, "*.zip")

            files = list(set(glob.glob(pattern_tar) + glob.glob(pattern_zip)))

            if len(files) > max_copies:
                files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                files_to_delete = files[max_copies:]

                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        logger.info(f"🗑️ [Retención] Backup antiguo eliminado: {os.path.basename(file_path)}")
                    except Exception as err:
                        logger.error(f"❌ [Retención Error] Error al eliminar '{file_path}': {err}")
        except Exception as e:
            logger.error(f"❌ [Retención Error] Error aplicando política de retención: {e}")

    async def _broadcast_ws(self, data: Dict[str, Any]) -> None:
        try:
            if hasattr(ws_manager, "broadcast_json"):
                fn = getattr(ws_manager, "broadcast_json")
                if asyncio.iscoroutinefunction(fn):
                    await fn(data)
                else:
                    fn(data)
            elif hasattr(ws_manager, "broadcast"):
                fn = getattr(ws_manager, "broadcast")
                msg = json.dumps(data)
                if asyncio.iscoroutinefunction(fn):
                    await fn(msg)
                else:
                    fn(msg)
        except Exception as e:
            logger.warning(f"[WebSocket] Error transmitiendo progreso: {e}")

    def prepare(self, backup_job: BackupJob) -> BackupManifest:
        return self.manifest_builder.build(backup_job)

    async def execute_restore_1click(self, app_name: str, file_path: str, target_path: Optional[str] = None) -> Dict[str, Any]:
        if not target_path:
            target_path = f"/DATA/AppData/{app_name}"

        dest_dir = Path(target_path)
        dest_dir.mkdir(parents=True, exist_ok=True)
        archive_path = Path(file_path)

        if not archive_path.exists():
            raise FileNotFoundError(f"El archivo de backup {file_path} no existe.")

        container_obj = None
        was_running = False

        if self.docker_client:
            try:
                containers = self.docker_client.containers.list(all=True)
                for c in containers:
                    if c.name.lower() == app_name.lower():
                        container_obj = c
                        if c.status == "running":
                            was_running = True
                            logger.info(f"[Restore] Deteniendo contenedor '{app_name}'...")
                            await self._broadcast_ws({
                                "type": "restore_progress",
                                "app": app_name,
                                "status": f"Deteniendo contenedor {app_name}..."
                            })
                            c.stop(timeout=15)
                        break
            except Exception as e:
                logger.error(f"[Restore] Error gestionando Docker para {app_name}: {e}")

        logger.info(f"[Restore] Extrayendo {archive_path} en {dest_dir}...")
        await self._broadcast_ws({
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
                raise ValueError(f"Formato no soportado: {archive_path.name}")
        except Exception as e:
            logger.error(f"[Restore] Error en la extracción para {app_name}: {e}")
            if container_obj and was_running:
                try:
                    container_obj.start()
                except Exception:
                    pass
            raise RuntimeError(f"Error en la extracción de datos: {e}")

        if container_obj and was_running:
            try:
                logger.info(f"[Restore] Reiniciando contenedor '{app_name}'...")
                await self._broadcast_ws({
                    "type": "restore_progress",
                    "app": app_name,
                    "status": f"Iniciando contenedor {app_name}..."
                })
                container_obj.start()
            except Exception as e:
                logger.error(f"[Restore] Error reanudando contenedor {app_name}: {e}")

        msg = f"Restauración completada con éxito para '{app_name}'"
        logger.info(f"[Restore] {msg}")

        await self._broadcast_ws({
            "type": "restore_complete",
            "app": app_name,
            "status": "COMPLETED",
            "message": msg
        })

        if hasattr(notification_service, "send_telegram"):
            try:
                res = notification_service.send_telegram(
                    f"✅ *Restauración Exitosa*\n*App:* `{app_name}`\n*Origen:* `{archive_path.name}`"
                )
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.warning(f"[Telegram] Error enviando notificación: {e}")

        return {
            "status": "SUCCESS",
            "app_name": app_name,
            "target_path": str(dest_dir),
            "snapshot_id": archive_path.name
        }

backup_engine_service = BackupEngineService()