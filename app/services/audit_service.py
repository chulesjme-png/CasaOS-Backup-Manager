import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger("casaos-backup")

DB_PATH = Path("/DATA/AppData/casaos-backup-manager/history.db")

class AuditService:
    def __init__(self):
        self._init_db()

    def _get_connection(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(DB_PATH)

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS execution_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_type TEXT NOT NULL,       -- 'backup' o 'restore'
                        target_name TEXT NOT NULL,    -- 'transmission', 'Disaster Recovery Full', etc.
                        status TEXT NOT NULL,         -- 'success' o 'failed'
                        duration_seconds REAL,
                        message TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"[Audit DB Error] No se pudo inicializar la BD de historial: {e}")

    def log_execution(self, job_type: str, target_name: str, status: str, duration_seconds: float, message: str):
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (job_type, target_name, status, round(duration_seconds, 2), message, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
        except Exception as e:
            logger.error(f"[Audit Log Error] Error guardando registro: {e}")

    def get_logs(self, limit: int = 50) -> List[Dict]:
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM execution_logs ORDER BY id DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"[Audit Log Error] Error obteniendo historial: {e}")
            return []

    def clear_logs(self) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM execution_logs")
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[Audit Log Error] Error borrando historial: {e}")
            return False

audit_service = AuditService()