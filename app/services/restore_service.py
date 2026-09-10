import subprocess
import logging
from pathlib import Path
from app.services.staging_manager import StagingManager

logger = logging.getLogger("casaos-backup")

class RestoreService:
    @staticmethod
    def execute_safe_restore(
        file_path: str,
        app_name: str,
        task_id: str,
        target_base_path: str = "/DATA/AppData",
        engine: str = "auto",
        dry_run: bool = False
    ) -> bool:
        staging_mgr = StagingManager(base_app_data_path=target_base_path)
        
        backup_file = Path(file_path)
        if backup_file.exists() and backup_file.is_file():
            file_size = backup_file.stat().st_size
            if not staging_mgr.verify_disk_space(file_size):
                raise RuntimeError("Espacio de almacenamiento insuficiente para realizar la descompresión.")

        staging_path = staging_mgr.create_staging_area(task_id)

        try:
            is_tar = file_path.endswith(".tar.gz") or file_path.endswith(".tgz") or engine == "tar"
            
            if is_tar:
                cmd = ["tar", "-xzf", file_path, "-C", str(staging_path)]
                if dry_run:
                    cmd = ["tar", "-tzf", file_path]
            else:
                cmd = ["borg", "extract", file_path, f"--target={staging_path}"]
                if dry_run:
                    cmd.append("--dry-run")

            logger.info(f"Descomprimiendo en zona aislada: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                raise RuntimeError(f"Fallo al descomprimir respaldo: {result.stderr.strip()}")

            if dry_run:
                logger.info("Verificación dry-run finalizada con éxito.")
                staging_mgr.cleanup_staging(task_id)
                return True

            staging_mgr.atomic_swap(task_id, app_name)
            staging_mgr.cleanup_staging(task_id)
            return True

        except Exception as e:
            logger.error(f"Error procesando la restauración segura: {e}")
            staging_mgr.cleanup_staging(task_id)
            raise e