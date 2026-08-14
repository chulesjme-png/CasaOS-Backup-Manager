import os
import logging
from typing import Dict, Any
from app.core.config import config_manager
from app.services.audit_service import audit_service

logger = logging.getLogger("casaos-backup")

class RetentionService:
    def __init__(self, max_backups_per_app: int = 3):
        self.max_backups_per_app = max_backups_per_app

    def clean_old_backups(self, max_keep: int = None) -> Dict[str, Any]:
        """
        Conserva únicamente las últimas N copias de seguridad por cada aplicación
        y por Disaster Recovery, eliminando automáticamente las sobrantes.
        """
        limit = max_keep if max_keep is not None else self.max_backups_per_app
        target_disk = config_manager.config.selected_target_disk

        if not target_disk or not os.path.exists(target_disk):
            logger.warning(f"[Retention] Disco de destino no disponible: {target_disk}")
            return {"deleted_files": 0, "freed_mb": 0}

        deleted_count = 0
        freed_bytes = 0

        # Carpetas base donde se alojan los respaldos
        backup_roots = [
            os.path.join(target_disk, "Backups", "Apps"),
            os.path.join(target_disk, "Backups", "DisasterRecovery")
        ]

        for root_dir in backup_roots:
            if not os.path.exists(root_dir):
                continue

            # Si estamos en Apps, escaneamos la subcarpeta de cada app individual
            if root_dir.endswith("Apps"):
                app_dirs = [
                    os.path.join(root_dir, d) for d in os.listdir(root_dir) 
                    if os.path.isdir(os.path.join(root_dir, d))
                ]
            else:
                app_dirs = [root_dir]

            for folder in app_dirs:
                try:
                    files = [
                        os.path.join(folder, f) for f in os.listdir(folder)
                        if (f.endswith(".tar.gz") or f.endswith(".tgz")) and os.path.isfile(os.path.join(folder, f))
                    ]

                    # Ordenar por fecha de modificación (de más reciente a más antigua)
                    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

                    # Si supera el límite de 3 copias, borrar las sobrantes
                    if len(files) > limit:
                        to_delete = files[limit:]
                        for filepath in to_delete:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            deleted_count += 1
                            freed_bytes += file_size
                            logger.info(f"[Retention] Eliminada copia antigua ({limit} máx. permitidas): {filepath}")

                except Exception as e:
                    logger.error(f"[Retention] Error analizando retención en {folder}: {e}")

        freed_mb = round(freed_bytes / (1024 * 1024), 2)
        if deleted_count > 0:
            summary = f"Limpieza completada: se eliminaron {deleted_count} copias antiguas y se liberaron {freed_mb} MB."
            logger.info(f"[Retention] {summary}")
            try:
                audit_service.log_event("CLEANUP", "ALL", "SUCCESS", summary)
            except Exception:
                pass
        else:
            logger.info(f"[Retention] Ninguna aplicación supera el límite de {limit} copias.")

        return {"deleted_files": deleted_count, "freed_mb": freed_mb}

retention_service = RetentionService(max_backups_per_app=3)