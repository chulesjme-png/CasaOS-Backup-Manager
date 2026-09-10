import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("casaos-backup")

class StagingManager:
    def __init__(self, base_app_data_path: str = "/DATA/AppData"):
        self.base_path = Path(base_app_data_path)
        self.staging_root = self.base_path / ".restore_staging"

    def verify_disk_space(self, required_bytes: int, safety_margin: float = 1.5) -> bool:
        target_dir = self.base_path if self.base_path.exists() else Path("/")
        try:
            total, used, free = shutil.disk_usage(target_dir)
            needed_bytes = int(required_bytes * safety_margin)
            if free < needed_bytes:
                logger.error(f"❌ Espacio en disco insuficiente. Libre: {free} B, Requerido con margen: {needed_bytes} B")
                return False
            return True
        except Exception as e:
            logger.warning(f"⚠️ No se pudo verificar el espacio en disco: {e}")
            return True

    def create_staging_area(self, task_id: str) -> Path:
        task_staging = self.staging_root / task_id
        task_staging.mkdir(parents=True, exist_ok=True)
        return task_staging

    def create_backup_snapshot(self, app_name: str) -> Optional[Path]:
        app_dir = self.base_path / app_name
        if not app_dir.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.base_path / f"{app_name}.bak_{timestamp}"
        logger.info(f"🛡️ Creando respaldo preventivo pre-restauración en: {backup_dir}")
        shutil.copytree(app_dir, backup_dir)
        return backup_dir

    def atomic_swap(self, task_id: str, app_name: str) -> bool:
        staging_app_dir = self.staging_root / task_id
        target_app_dir = self.base_path / app_name
        
        if not staging_app_dir.exists():
            raise FileNotFoundError(f"Directorio de staging no existe: {staging_app_dir}")

        backup_dir = None
        if target_app_dir.exists():
            backup_dir = self.create_backup_snapshot(app_name)
            shutil.rmtree(target_app_dir)

        try:
            shutil.move(str(staging_app_dir), str(target_app_dir))
            logger.info(f"✅ Intercambio atómico completado exitosamente para {app_name}")
            if backup_dir and backup_dir.exists():
                shutil.rmtree(backup_dir)
            return True
        except Exception as e:
            logger.error(f"💥 Error en el intercambio atómico: {e}. Iniciando rollback inmediato...")
            if backup_dir and backup_dir.exists():
                if target_app_dir.exists():
                    shutil.rmtree(target_app_dir)
                shutil.move(str(backup_dir), str(target_app_dir))
                logger.info(f"🔄 Rollback completado: {app_name} restaurado a su estado previo.")
            raise RuntimeError(f"Fallo en la sustitución de archivos. Rollback completado con éxito: {e}")

    def cleanup_staging(self, task_id: str):
        task_staging = self.staging_root / task_id
        if task_staging.exists():
            shutil.rmtree(task_staging)
        if self.staging_root.exists() and not any(self.staging_root.iterdir()):
            shutil.rmtree(self.staging_root)