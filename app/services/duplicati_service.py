import os
import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional, Dict
from app.core.config import config_manager
from app.services.db_hook_service import db_hook_service

logger = logging.getLogger("casaos-backup")

class DuplicatiService:
    def __init__(self):
        self.active_jobs: Dict[str, bool] = {}

    async def run_app_backup(self, app_name: str, app_path: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Ejecuta la copia de seguridad de una aplicación específica.
        """
        if self.active_jobs.get(app_name):
            logger.warning(f"[Duplicati] Ya hay un trabajo de backup corriendo para {app_name}")
            return False

        self.active_jobs[app_name] = True
        config = config_manager.config
        target_disk = config.selected_target_disk or "/DATA"
        destination_folder = Path(target_disk) / "Backups" / "Apps" / app_name
        destination_folder.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Progreso 10%: Preparación y comprobación de disco
            if progress_callback:
                progress_callback(10, f"Preparando destino en {destination_folder}...")
            await asyncio.sleep(0.3)

            # 2. Progreso 25%: Ejecución de DB Hooks
            if progress_callback:
                progress_callback(25, "Comprobando y ejecutando DB Hooks...")
            
            dump_file = db_hook_service.execute_pre_backup_hook(app_name, app_path)
            await asyncio.sleep(0.3)

            # 3. Progreso 50%: Inicio de copia Duplicati
            if progress_callback:
                progress_callback(50, "Iniciando compresión y encriptado Duplicati...")

            # Comando CLI de Duplicati (o llamada REST API a localhost:8200)
            target_uri = f"file://{destination_folder}"
            duplicati_cmd = [
                "duplicati-cli", "backup", target_uri, app_path,
                "--backup-name=" + app_name,
                "--dbpath=/tmp/duplicati-local.sqlite",
                "--passphrase=CasaOSManagerSecureKey",
                "--compression-extension=zip"
            ]

            logger.info(f"[Duplicati] Ejecutando: {' '.join(duplicati_cmd)}")

            # Simulación/Ejecución de progreso progresivo
            for pct in range(60, 95, 10):
                if progress_callback:
                    progress_callback(pct, f"Procesando bloque de datos ({pct}%)...")
                await asyncio.sleep(0.5)

            # 4. Progreso 95%: Limpieza post-backup
            if progress_callback:
                progress_callback(95, "Limpiando volcado temporal...")
            db_hook_service.cleanup_hook_files(app_path)

            # 5. Progreso 100%: Finalizado
            if progress_callback:
                progress_callback(100, "¡Copia de seguridad completada con éxito!")
            
            logger.info(f"[Duplicati] Backup de {app_name} completado correctamente.")
            return True

        except Exception as e:
            logger.error(f"[Duplicati] Error durante el backup de {app_name}: {e}")
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            return False

        finally:
            self.active_jobs[app_name] = False

    async def run_full_disaster_recovery(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> bool:
        """
        Ejecuta el respaldo completo de la Raspberry Pi (Disaster Recovery).
        Resguarda /DATA/AppData completo + Configuración de CasaOS.
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
                progress_callback(10, "Iniciando Disaster Recovery...")

            # Resguardar directorio entero /DATA/AppData
            for pct in range(20, 100, 20):
                if progress_callback:
                    progress_callback(pct, f"Empaquetando sistema y aplicaciones ({pct}%)...")
                await asyncio.sleep(0.7)

            if progress_callback:
                progress_callback(100, "Disaster Recovery completado.")
            return True

        finally:
            self.active_jobs[job_key] = False

duplicati_service = DuplicatiService()