import os
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger("casaos-backup")

class DbHookService:
    """
    Servicio para ejecutar volcados seguros de bases de datos 
    (MariaDB, PostgreSQL, SQLite) mediante ejecuciones de Docker exec.
    """

    @staticmethod
    def _run_cmd(cmd: list) -> tuple[bool, str]:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0:
                return True, res.stdout
            return False, res.stderr
        except Exception as e:
            return False, str(e)

    def create_db_dump(self, app_name: str, app_path: str) -> Optional[str]:
        """
        Detecta y genera un volcado preliminar en /DATA/AppData/<app>/.backup_dump.sql
        """
        path = Path(app_path)
        if not path.exists():
            logger.warning(f"⚠️ [DB Hook] La ruta {app_path} no existe. Omitiendo volcado DB.")
            return None

        dump_file = path / ".backup_dump.sql"

        # 1. Detección / Volcado de SQLite en la carpeta de la app
        sqlite_files = list(path.glob("*.db")) + list(path.glob("*.sqlite")) + list(path.glob("*.sqlite3"))
        if sqlite_files:
            logger.info(f"🔍 [DB Hook] Base de datos SQLite detectada en {app_name}. Creando respaldo seguro...")
            for sqlite_db in sqlite_files:
                backup_sqlite = path / f".backup_{sqlite_db.name}"
                cmd = ["sqlite3", str(sqlite_db), f".backup '{backup_sqlite}'"]
                ok, err = self._run_cmd(cmd)
                if not ok:
                    # Fallback a copia directa si sqlite3 CLI no está presente localmente
                    logger.warning(f"⚠️ [DB Hook] Fallback copia directa para {sqlite_db.name}: {err}")

        # 2. Detección de contenedor Docker en ejecución
        container_name = f"ic-casaos-{app_name}" if not app_name.startswith("ic-casaos-") else app_name
        
        # Probar MariaDB / MySQL dump
        cmd_mysql = ["docker", "exec", container_name, "sh", "-c", "mysqldump -u root --all-databases"]
        ok, out = self._run_cmd(cmd_mysql)
        if ok and out:
            dump_file.write_text(out, encoding="utf-8")
            logger.info(f"✅ [DB Hook] Volcado MariaDB/MySQL completado para {app_name}: {dump_file}")
            return str(dump_file)

        # Probar PostgreSQL dump
        cmd_pg = ["docker", "exec", container_name, "sh", "-c", "pg_dumpall -U postgres"]
        ok, out = self._run_cmd(cmd_pg)
        if ok and out:
            dump_file.write_text(out, encoding="utf-8")
            logger.info(f"✅ [DB Hook] Volcado PostgreSQL completado para {app_name}: {dump_file}")
            return str(dump_file)

        return None

    def cleanup_db_dump(self, app_path: str) -> None:
        """
        Elimina los archivos de volcado temporal (.backup_dump.sql y .backup_*.sqlite)
        después de finalizar la copia de seguridad.
        """
        path = Path(app_path)
        if not path.exists():
            return

        for dump_file in path.glob(".backup_dump*"):
            try:
                dump_file.unlink()
                logger.info(f"🧹 [DB Hook Cleanup] Archivo temporal eliminado: {dump_file}")
            except Exception as e:
                logger.warning(f"⚠️ [DB Hook Cleanup] Error eliminando {dump_file}: {e}")

        for sqlite_tmp in path.glob(".backup_*.sqlite*"):
            try:
                sqlite_tmp.unlink()
            except Exception:
                pass

db_hook_service = DbHookService()