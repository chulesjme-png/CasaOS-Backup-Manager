import subprocess
import logging
import os

logger = logging.getLogger(__name__)

class BackupHooks:
    @staticmethod
    def run_pre_backup_hook(app_name: str, app_path: str) -> bool:
        """
        Ejecuta acciones previas a la copia según la aplicación detectada.
        Devuelve True si el hook fue exitoso o no era necesario.
        """
        app_name_lower = app_name.lower()
        
        logger.info(f"🔍 Comprobando Pre-Backup Hook para: {app_name}")

        # HOOK 1: Immich / PostgreSQL
        if "immich" in app_name_lower or "postgres" in app_name_lower:
            return BackupHooks._hook_immich_postgres(app_path)

        # HOOK 2: Nextcloud (Ejemplo: Activar modo mantenimiento si fuera necesario)
        # elif "nextcloud" in app_name_lower:
        #     return BackupHooks._hook_nextcloud_maintenance(True)

        return True

    @staticmethod
    def run_post_backup_hook(app_name: str, app_path: str) -> bool:
        """
        Ejecuta acciones posteriores a la copia (limpieza de dumps, reactivación de servicios).
        """
        app_name_lower = app_name.lower()

        if "immich" in app_name_lower or "postgres" in app_name_lower:
            # Limpiar el volcado SQL temporal tras completar la copia
            dump_file = os.path.join(app_path, "immich_db_backup.sql")
            if os.path.exists(dump_file):
                try:
                    os.remove(dump_file)
                    logger.info(f"🧹 Limpieza de dump temporal realizada: {dump_file}")
                except Exception as e:
                    logger.warning(f"No se pudo eliminar el dump temporal: {e}")

        return True

    @staticmethod
    def _hook_immich_postgres(app_path: str) -> bool:
        """
        Ejecuta un pg_dump dentro del contenedor de postgres de Immich
        y guarda el archivo .sql directamente en la carpeta de appdata.
        """
        target_file = os.path.join(app_path, "immich_db_backup.sql")
        
        # Comando docker exec para volcar la BD
        cmd = [
            "docker", "exec", "immich-postgres",
            "pg_dumpall", "-U", "postgres"
        ]

        try:
            logger.info("⚡ Ejecutando Hook DB: Volcado pg_dumpall para immich-postgres...")
            os.makedirs(app_path, exist_ok=True)
            
            with open(target_file, "w", encoding="utf-8") as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True, check=True)
                
            logger.info(f"✅ Dump de BD generado correctamente en: {target_file}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error al ejecutar pg_dump en immich-postgres: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"❌ Error inesperado en el Hook de Immich: {e}")
            return False