import os
import sqlite3
import time
import logging
import tarfile
import subprocess
import shutil
import socket
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

# Importación del servicio de discos corregido
from app.services.disk_service import disk_service

logger = logging.getLogger("casaos-backup")
logging.basicConfig(level=logging.INFO)

DB_PATH = Path("/DATA/AppData/casaos-backup-manager/history.db")
BASE_DIR = Path(__file__).resolve().parent

active_jobs = {}

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

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

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

# Detección de contenedores Docker
@app.get("/api/v1/system/docker")
def get_docker_containers():
    containers = []
    socket_path = "/var/run/docker.sock"
    
    if os.path.exists(socket_path):
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(socket_path)
            s.sendall(b"GET /containers/json HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            
            response = b""
            while True:
                data = s.recv(4096)
                if not data:
                    break
                response += data
            s.close()
            
            parts = response.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                body = parts[1].decode('utf-8', errors='ignore')
                if "Transfer-Encoding: chunked" in parts[0].decode('utf-8', errors='ignore'):
                    lines = body.split("\r\n")
                    json_str = "".join([lines[i] for i in range(1, len(lines), 2) if i < len(lines)])
                    data = json.loads(json_str)
                else:
                    data = json.loads(body)
                
                for c in data:
                    names = [n.lstrip("/") for n in c.get("Names", [""])]
                    containers.append({
                        "name": names[0] if names else c.get("Id", "")[:12],
                        "status": c.get("Status", "Running"),
                        "image": c.get("Image", "")
                    })
                return {"containers": containers}
        except Exception as e:
            logger.error(f"Error socket Docker: {e}")

    try:
        cmd = ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().split("\n"):
                parts = line.split("|")
                if len(parts) == 3:
                    containers.append({"name": parts[0], "status": parts[1], "image": parts[2]})
    except Exception:
        pass

    return {"containers": containers}

# Obtener puntos de montaje desde disk_service
def get_all_mounts():
    disks = disk_service.get_disks()
    return [d["mountpoint"] for d in disks]

@app.get("/api/v1/system/disks")
def get_disks():
    return {"disks": disk_service.get_disks()}

def perform_real_backup(app_name: str, target_disk: str, job_id: str):
    start = time.time()
    active_jobs[job_id] = {"status": "running", "progress": 10, "message": "Preparando archivos...", "cancelled": False}
    
    if target_disk and os.path.exists(target_disk):
        base_dest = Path(target_disk)
    else:
        base_dest = Path("/DATA/Backups")
        
    dest_dir = base_dest / "Backups" / "Apps" / app_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{app_name.lower()}_backup_{timestamp}.tar.gz"
    dest_file = dest_dir / filename

    src_dir = Path("/DATA/AppData") if app_name == "Sistema_Completo" else Path(f"/DATA/AppData/{app_name}")

    try:
        if not src_dir.exists():
            active_jobs[job_id] = {"status": "failed", "progress": 100, "message": f"Origen {src_dir} no existe"}
            return

        active_jobs[job_id]["progress"] = 35
        active_jobs[job_id]["message"] = f"Comprimiendo {src_dir.name}..."

        with tarfile.open(dest_file, "w:gz") as tar:
            for root, _, files in os.walk(src_dir):
                if active_jobs[job_id].get("cancelled"):
                    if dest_file.exists(): os.remove(dest_file)
                    active_jobs[job_id] = {"status": "cancelled", "progress": 0, "message": "Proceso cancelado por el usuario"}
                    return
                for f in files:
                    fp = os.path.join(root, f)
                    tar.add(fp, arcname=os.path.relpath(fp, src_dir))

        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "success", "progress": 100, "message": "Copia completada con éxito", "file": filename}

        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup", app_name, "success", elapsed, filename, int(time.time() * 1000))
            )
            conn.commit()

    except Exception as e:
        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": str(e)}
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup", app_name, "failed", elapsed, str(e), int(time.time() * 1000))
            )
            conn.commit()

@app.post("/api/v1/backups/run-app/{app_name}")
def run_backup(app_name: str, background_tasks: BackgroundTasks, target_disk: str = Query(None)):
    job_id = f"job_{app_name}_{int(time.time())}"
    background_tasks.add_task(perform_real_backup, app_name, target_disk, job_id)
    return {"status": "started", "job_id": job_id}

@app.get("/api/v1/backups/job-status/{job_id}")
def get_job_status(job_id: str):
    return active_jobs.get(job_id, {"status": "unknown", "progress": 0, "message": "Iniciando..."})

@app.post("/api/v1/backups/cancel/{job_id}")
def cancel_job(job_id: str):
    if job_id in active_jobs:
        active_jobs[job_id]["cancelled"] = True
        return {"status": "cancelled"}
    return {"status": "not_found"}

@app.get("/api/v1/backups/list")
@app.get("/api/v1/backups")
def list_backups():
    backups = []
    seen_files = set()
    mounts = get_all_mounts()

    for m in mounts:
        target_path = f"/host{m}" if os.path.exists(f"/host{m}") else m
        if os.path.exists(target_path):
            for root, _, files in os.walk(target_path):
                for file in files:
                    fn_lower = file.lower()
                    if fn_lower.startswith("duplicati-") or "dblock" in fn_lower or "dindex" in fn_lower or "dlist" in fn_lower:
                        continue
                    
                    if fn_lower.endswith((".tar.gz", ".tgz", ".zip")) and fn_lower not in seen_files:
                        fp = os.path.join(root, file)
                        try:
                            stats = os.stat(fp)
                            dt = datetime.fromtimestamp(stats.st_mtime)
                            size_mb = round(stats.st_size / (1024 * 1024), 2)
                            size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(stats.st_size/1024, 1)} KB"
                            
                            app_name = file.split("_")[0].capitalize() if "_" in file else "Sistema"
                            seen_files.add(fn_lower)

                            backups.append({
                                "filename": file,
                                "app_name": app_name,
                                "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                                "size_str": size_str,
                                "timestamp": stats.st_mtime
                            })
                        except Exception:
                            pass

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"backups": backups}

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
            dur_val = round(r["duration_seconds"] or 0.1, 1)
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