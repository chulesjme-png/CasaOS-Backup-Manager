import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger("casaos-backup")

class DBHookService:
    def __init__(self):
        # Mapeo de contenedores y sus estrategias de backup
        self.known_db_types = {
            "mariadb": "mysql",
            "mysql": "mysql",
            "postgres": "postgres",
            "postgresql": "postgres",
            "immich-postgres": "postgres"
        }

    def execute_pre_backup_hook(self, app_name: str, app_path: str) -> Optional[str]:
        """
        Ejecuta el dump de la base de datos antes del backup de archivos.
        Devuelve la ruta del archivo .sql generado si tuvo éxito.
        """
        app_name_lower = app_name.lower()
        dump_file_path = Path(app_path) / ".backup_dump.sql"

        # 1. Estrategia MariaDB / MySQL
        if "mariadb" in app_name_lower or "mysql" in app_name_lower:
            logger.info(f"[DB Hook] Detectado MariaDB/MySQL para {app_name}. Iniciando dump...")
            return self._dump_mysql(app_name, dump_file_path)

        # 2. Estrategia PostgreSQL
        elif "postgres" in app_name_lower or "immich" in app_name_lower:
            logger.info(f"[DB Hook] Detectado PostgreSQL para {app_name}. Iniciando dump...")
            return self._dump_postgres(app_name, dump_file_path)

        # 3. Estrategia SQLite (Verificación de archivos .db / .sqlite en app_path)
        sqlite_files = list(Path(app_path).rglob("*.sqlite")) + list(Path(app_path).rglob("*.db"))
        if sqlite_files:
            logger.info(f"[DB Hook] Detectado SQLite en {app_name}. Ejecutando backup seguro de tablas...")
            return self._dump_sqlite(sqlite_files[0], dump_file_path)

        return None

    def _dump_mysql(self, container_name: str, output_path: Path) -> Optional[str]:
        """Ejecuta mysqldump dentro del contenedor Docker"""
        cmd = [
            "docker", "exec", container_name,
            "sh", "-c", f"mysqldump --all-databases -u root -p$MYSQL_ROOT_PASSWORD > {output_path}"
        ]
        return self._run_command(cmd, output_path)

    def _dump_postgres(self, container_name: str, output_path: Path) -> Optional[str]:
        """Ejecuta pg_dumpall dentro del contenedor Docker"""
        cmd = [
            "docker", "exec", container_name,
            "sh", "-c", f"pg_dumpall -U postgres > {output_path}"
        ]
        return self._run_command(cmd, output_path)

    def _dump_sqlite(self, db_file: Path, output_path: Path) -> Optional[str]:
        """Copia caliente consistente de SQLite usando el comando .backup"""
        cmd = ["sqlite3", str(db_file), f".backup '{output_path}'"]
        return self._run_command(cmd, output_path)

    def cleanup_hook_files(self, app_path: str):
        """Elimina el dump temporal tras el backup"""
        dump_file = Path(app_path) / ".backup_dump.sql"
        if dump_file.exists():
            try:
                os.remove(dump_file)
                logger.info(f"[DB Hook] Archivo temporal limpiado: {dump_file}")
            except Exception as e:
                logger.error(f"[DB Hook] Error al limpiar {dump_file}: {e}")

    def _run_command(self, cmd: list, output_path: Path) -> Optional[str]:
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
            if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
                logger.info(f"[DB Hook] Dump exitoso generado en {output_path} ({output_path.stat().st_size} bytes)")
                return str(output_path)
            else:
                logger.warning(f"[DB Hook] Advertencia en dump: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"[DB Hook] Error ejecutando comando de dump: {e}")
            return None

db_hook_service = DBHookService()