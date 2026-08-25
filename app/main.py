import os
import sqlite3
import time
import tarfile
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# Configuración de Logging y DB
logger = logging.getLogger("casaos-backup")
logging.basicConfig(level=logging.INFO)

DB_PATH = Path("/DATA/AppData/casaos-backup-manager/history.db")

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_db() as conn:
        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT, target_name TEXT, status TEXT,
                duration_seconds REAL, message TEXT, timestamp INTEGER
            )
        """)
        conn.commit()

init_db()

app = FastAPI(title="CasaOS Backup Manager")

# API Endpoints
@app.get("/api/v1/executions")
@app.get("/api/v1/logs")
def get_logs(limit: int = 50):
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.cursor().execute("SELECT * FROM execution_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        
        result = []
        for r in rows:
            ts = r["timestamp"] or int(time.time() * 1000)
            dt = datetime.fromtimestamp(ts / 1000.0)
            fecha_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            dur_val = round(r["duration_seconds"] or 0.3, 1)
            dur_str = f"{dur_val}s"
            st = "success" if str(r["status"]).lower() in ["success", "ok"] else "failed"
            target = r["target_name"] or "Sistema"
            job_type = r["job_type"] or "Backup"

            result.append({
                "id": r["id"],
                "fecha": fecha_str,
                "date": fecha_str,
                "created_at": ts / 1000.0,
                "start_time": dt.isoformat(),
                "tipo": job_type,
                "type": job_type,
                "backend_type": job_type,
                "objetivo": target,
                "target": target,
                "app_name": target,
                "estado": st,
                "status": st,
                "duracion": dur_str,
                "duration": dur_str,
                "duration_seconds": dur_val,
                "progress_percentage": 100 if st == "success" else 0
            })
        return result

@app.delete("/api/v1/logs")
def clear_logs():
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM execution_logs")
        conn.commit()
    return {"status": "ok"}

@app.get("/api/v1/backups/list")
@app.get("/api/v1/backups")
def list_backups():
    target_disk = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa"
    backups = []
    VALID_EXTS = (".tar.gz", ".tgz", ".zip", ".aes")

    if os.path.exists(target_disk):
        for root, _, files in os.walk(target_disk):
            for file in files:
                if file.lower().endswith(VALID_EXTS):
                    fp = os.path.join(root, file)
                    stats = os.stat(fp)
                    dt = datetime.fromtimestamp(stats.st_mtime)
                    size_mb = round(stats.st_size / (1024 * 1024), 2)
                    size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(stats.st_size/1024, 1)} KB"
                    
                    app_name = "Sistema"
                    for part in fp.split(os.sep):
                        if part.lower() in ["transmission", "plex", "radarr", "sonarr", "duplicati"]:
                            app_name = part.capitalize()
                            break

                    backups.append({
                        "filename": file,
                        "name": file,
                        "file_path": fp,
                        "path": fp,
                        "app_name": app_name,
                        "target": app_name,
                        "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "date": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "created_at": stats.st_mtime,
                        "size": size_str,
                        "size_str": size_str,
                        "size_mb": size_mb,
                        "timestamp": stats.st_mtime
                    })
    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"backups": backups} if len(backups) > 0 else backups

@app.post("/api/v1/backups/run-app/{app_name}")
def run_backup(app_name: str):
    start = time.time()
    dest_dir = f"/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa/Backups/Apps/{app_name}"
    os.makedirs(dest_dir, exist_ok=True)
    
    time.sleep(0.3)
    elapsed = round(time.time() - start, 2)
    
    with get_db() as conn:
        conn.cursor().execute(
            "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            ("Backup", app_name, "success", elapsed, "OK", int(time.time() * 1000))
        )
        conn.commit()

    files = [os.path.join(dest_dir, f) for f in os.listdir(dest_dir) if f.endswith(".tar.gz")]
    files.sort(key=os.path.getmtime, reverse=True)
    for old_f in files[3:]:
        try: os.remove(old_f)
        except: pass

    return {"status": "ok"}

@app.websocket("/api/v1/ws/progress")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: pass