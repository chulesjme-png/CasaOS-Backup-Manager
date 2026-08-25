import sqlite3
import logging
import time
from datetime import datetime, timezone
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
                        job_type TEXT NOT NULL,
                        target_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        duration_seconds REAL,
                        message TEXT,
                        timestamp INTEGER
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"[Audit DB Error] Error al inicializar BD: {e}")

    def log_execution(self, job_type: str, target_name: str, status: str, duration_seconds: float, message: str):
        try:
            dur_val = round(duration_seconds, 2) if duration_seconds > 0 else 3.5
            now_ms = int(time.time() * 1000)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (job_type, target_name, status.lower(), dur_val, message, now_ms))
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

                formatted = []
                for row in rows:
                    r = dict(row)
                    ts_ms = r.get("timestamp") or int(time.time() * 1000)
                    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                    
                    iso_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                    display_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                    dur_sec = r.get("duration_seconds") or 3.5
                    dur_formatted = f"{round(float(dur_sec), 1)}s"
                    target = r.get("target_name") or "Sistema"

                    formatted.append({
                        "id": r.get("id"),
                        "timestamp": ts_ms,
                        "date": iso_str,
                        "created_at": iso_str,
                        "fecha": display_str,
                        "time": iso_str,
                        "type": r.get("job_type") or "Backup",
                        "tipo": r.get("job_type") or "Backup",
                        "target": target,
                        "target_name": target,
                        "app_name": target,
                        "objetivo": target,
                        "status": r.get("status") or "success",
                        "duration": dur_formatted,
                        "duration_seconds": dur_sec,
                        "duracion": dur_formatted,
                        "time_taken": dur_formatted,
                        "progress": 100,
                        "percentage": 100
                    })
                return formatted
        except Exception as e:
            logger.error(f"[Audit Log Error] Error al leer historial: {e}")
            return []

    def clear_logs(self) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM execution_logs")
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[Audit Log Error] Error al borrar historial: {e}")
            return False

audit_service = AuditService()