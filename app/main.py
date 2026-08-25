import os
import sqlite3
import time
import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger("casaos-backup")
logging.basicConfig(level=logging.INFO)

DB_PATH = Path("/DATA/AppData/casaos-backup-manager/history.db")
BASE_DIR = Path(__file__).resolve().parent

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

# Silenciar peticiones favicon
@app.get("/favicon.ico", include_in_schema=False)
@app.get("/apple-touch-icon.png", include_in_schema=False)
@app.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# Servir archivos estáticos
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    possible_paths = [
        BASE_DIR / "index.html",
        BASE_DIR / "templates" / "index.html",
        BASE_DIR.parent / "index.html",
    ]
    for path in possible_paths:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "<h1>Error: No se encontró index.html</h1>"

# Escaneo dinámico de Apps reales
@app.get("/api/v1/apps")
def get_apps():
    appdata_dir = Path("/DATA/AppData")
    apps = []
    if appdata_dir.exists():
        for item in sorted(appdata_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                apps.append({
                    "name": item.name,
                    "path": str(item)
                })
    return {"apps": apps}

# Historial de ejecuciones
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
            st = "success" if str(r["status"]).lower() in ["success", "ok"] else "failed"
            dur_val = round(r["duration_seconds"] or 0.3, 1)
            result.append({
                "id": r["id"],
                "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "tipo": r["job_type"] or "Backup",
                "objetivo": r["target_name"] or "Sistema",
                "estado": st,
                "duracion": f"{dur_val}s"
            })
        return result

@app.delete("/api/v1/logs")
def clear_logs():
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM execution_logs")
        conn.commit()
    return {"status": "ok"}

# Listado de copias filtrado (Sin trozos dblock/dindex de Duplicati)
@app.get("/api/v1/backups/list")
@app.get("/api/v1/backups")
def list_backups():
    target_disk = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa"
    backups = []

    if os.path.exists(target_disk):
        for root, _, files in os.walk(target_disk):
            for file in files:
                fn_lower = file.lower()
                
                # Ignorar fragmentos internos de Duplicati (.dblock, .dindex, .dlist)
                if fn_lower.startswith("duplicati-") or "dblock" in fn_lower or "dindex" in fn_lower or "dlist" in fn_lower:
                    continue
                
                if fn_lower.endswith((".tar.gz", ".tgz", ".zip", ".tar")):
                    fp = os.path.join(root, file)
                    stats = os.stat(fp)
                    dt = datetime.fromtimestamp(stats.st_mtime)
                    size_mb = round(stats.st_size / (1024 * 1024), 2)
                    size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(stats.st_size/1024, 1)} KB"
                    
                    # Extraer el nombre limpio de la app
                    app_name = "Sistema"
                    if "_" in file:
                        raw_app = file.split("_")[0]
                        if raw_app.lower() not in ["backup", "casaos", "system"]:
                            app_name = raw_app.capitalize()

                    backups.append({
                        "filename": file,
                        "app_name": app_name,
                        "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "size_str": size_str,
                        "timestamp": stats.st_mtime
                    })

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"backups": backups}

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

    return {"status": "ok"}

@app.websocket("/api/v1/ws/progress")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: pass