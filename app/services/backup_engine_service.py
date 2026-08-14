"""
Servicio principal del Backup Engine.

Orquesta la preparación de backups, la retención automática de archivos
y la ejecución automatizada de restauraciones "1-Click" (parada de contenedor, descompresión, arranque y notificación).
"""

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

    @staticmethod
    def apply_retention_policy(target_dir: str, prefix: str = "", max_copies: int = 3) -> None:
        """
        Revisa el directorio `target_dir` y conserva solo las `max_copies` más recientes (por defecto 3).
        Elimina automáticamente los archivos .tar.gz o .zip antiguos sobrantes.
        """
        try:
            if not target_dir or not os.path.exists(target_dir):
                logger.warning(f"[Retención] El directorio objetivo '{target_dir}' no existe.")
                return

            # Buscar respaldos .tar.gz y .zip en la carpeta
            if prefix:
                pattern_tar = os.path.join(target_dir, f"*{prefix}*.tar.gz")
                pattern_zip = os.path.join(target_dir, f"*{prefix}*.zip")
            else:
                pattern_tar = os.path.join(target_dir, "*.tar.gz")
                pattern_zip = os.path.join(target_dir, "*.zip")

            files = list(set(glob.glob(pattern_tar) + glob.glob(pattern_zip)))

            # Si excedemos el número máximo de copias permitidas
            if len(files) > max_copies:
                # Ordenar por fecha de modificación (el más reciente primero)
                files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

                files_to_delete = files[max_copies:]
                logger.info(
                    f"🧹 [Retención] Se encontraron {len(files)} copias en '{target_dir}' para '{prefix or 'general'}'. "
                    f"Aplicando límite de {max_copies} copias..."
                )

                for file_path in files_to_delete:
                    try:
                        os.remove(file_path)
                        logger.info(f"🗑️ [Retención] Backup antiguo eliminado: {os.path.basename(file_path)}")
                    except Exception as err:
                        logger.error(f"❌ [Retención Error] No se pudo eliminar '{file_path}': {err}")
            else:
                logger.info(f"ℹ️ [Retención] {len(files)}/{max_copies} copias conservadas en '{target_dir}'.")
        except Exception as e:
            logger.error(f"❌ [Retención Error] Error aplicando política de retención: {e}")

    async def _broadcast_ws(self, data: Dict[str, Any]) -> None:
        """
        Envia actualizaciones de progreso por WebSocket de forma ultra-segura,
        soportando tanto broadcast_json como broadcast con texto JSON.
        """
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
            logger.warning(f"[WebSocket] No se pudo transmitir evento de progreso: {e}")

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
                            await self._broadcast_ws({
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
                await self._broadcast_ws({
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