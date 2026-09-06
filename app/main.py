import os
import sqlite3
import time
import logging
import tarfile
import subprocess
import shutil
import socket
import json
import platform
import requests
import psutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, Query, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from app.services.disk_service import disk_service
except ImportError:
    class DummyDiskService:
        def get_disks(self):
            disks = []
            try:
                du = shutil.disk_usage("/DATA")
                disks.append({
                    "name": "DATA",
                    "mountpoint": "/DATA",
                    "total_gb": round(du.total / (1024**3), 2),
                    "used_gb": round(du.used / (1024**3), 2),
                    "free_gb": round(du.free / (1024**3), 2),
                    "percent": round((du.used / du.total) * 100, 1)
                })
            except Exception:
                pass
            return disks
    disk_service = DummyDiskService()

try:
    from app.services.duplicati_orchestrator_service import duplicati_orchestrator
except ImportError:
    class DummyDuplicatiOrchestrator:
        def run_full_disaster_recovery(self, *args, **kwargs):
            return {"success": False, "error": "Modulo orquestador de Duplicati no disponible."}
        def get_task_status(self, *args, **kwargs):
            return {"status": "error", "phase": "Failed", "progress": 0.0}
        def find_job_id_by_name(self, *args, **kwargs):
            return 1
    duplicati_orchestrator = DummyDuplicatiOrchestrator()

logger = logging.getLogger("casaos-backup")
logging.basicConfig(level=logging.INFO)

DB_PATH = Path("/DATA/AppData/casaos-backup-manager/history.db")
CONFIG_PATH = Path("/DATA/AppData/casaos-backup-manager/config.json")
BASE_DIR = Path(__file__).resolve().parent

active_jobs = {}

# --- MODELOS DE DATOS ---
class ConfigModel(BaseModel):
    target_disk: str = ""
    telegram_enabled: bool = False
    telegram_token: str = ""
    telegram_chat_id: str = ""
    duplicati_url: str = "http://172.17.0.1:8200"
    duplicati_password: str = ""

class TelegramTestModel(BaseModel):
    telegram_token: str = ""
    telegram_chat_id: str = ""
    token: str = ""
    chat_id: str = ""

# --- GESTIÓN DE CONFIGURACIÓN Y TELEGRAM ---
def load_config():
    defaults = {
        "target_disk": "",
        "telegram_enabled": False,
        "telegram_token": "",
        "telegram_chat_id": "",
        "duplicati_url": "http://172.17.0.1:8200",
        "duplicati_password": ""
    }
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            defaults.update(data)
            return defaults
        except Exception as e:
            logger.error(f"Error al leer la configuración: {e}")
    return defaults

def save_config_file(data: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def kill_rsync_processes():
    """Elimina todos los procesos rsync activos usando psutil nativo."""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and 'rsync' in proc.info['name'].lower():
                proc.kill()
                logger.info(f"[KILL] Proceso rsync {proc.info['pid']} finalizado.")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

def send_telegram_notification(message: str):
    cfg = load_config()
    if not cfg.get("telegram_enabled") or not cfg.get("telegram_token") or not cfg.get("telegram_chat_id"):
        logger.warning("Telegram no enviado: Configuración incompleta o deshabilitada.")
        return
    
    token = cfg['telegram_token'].strip()
    chat_id = cfg['telegram_chat_id'].strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=8)
        if res.status_code != 200:
            logger.error(f"Error Telegram API HTTP {res.status_code}: {res.text}")
    except Exception as e:
        logger.error(f"Error enviando notificación a Telegram: {e}")

# --- BASE DE DATOS ---
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

for candidate in [BASE_DIR / "static", BASE_DIR.parent / "static", Path("/app/static"), Path("/app/ui")]:
    if candidate.exists() and candidate.is_dir():
        app.mount("/static", StaticFiles(directory=candidate), name="static")
        break

@app.get("/", response_class=HTMLResponse)
def read_root():
    possible_paths = [
        BASE_DIR / "index.html",
        BASE_DIR / "templates" / "index.html",
        BASE_DIR / "static" / "index.html",
        BASE_DIR.parent / "index.html",
        BASE_DIR.parent / "templates" / "index.html",
        Path("/app/index.html"),
        Path("/app/app/index.html"),
        Path("/app/templates/index.html"),
        Path("/app/static/index.html"),
        Path("/app/ui/index.html"),
    ]
    for path in possible_paths:
        if path.exists():
            return path.read_text(encoding="utf-8")
    return "<h1>Error: No se encontró index.html</h1>"

# --- ENDPOINTS DE CONFIGURACIÓN Y SISTEMA ---
@app.get("/api/v1/system/info")
def get_system_info():
    model = "Raspberry Pi / Linux Host"
    try:
        if os.path.exists("/proc/device-tree/model"):
            model = Path("/proc/device-tree/model").read_text().strip().replace("\x00", "")
    except Exception:
        pass

    ram_info = "Disponible"
    try:
        if os.path.exists("/proc/meminfo"):
            lines = Path("/proc/meminfo").read_text().splitlines()
            mem_total = 0
            for l in lines:
                if l.startswith("MemTotal:"):
                    mem_total = int(l.split()[1]) // 1024
                    break
            if mem_total:
                ram_info = f"{round(mem_total / 1024, 1)} GB (Total)"
    except Exception:
        pass

    temp_info = "Normal / OK"
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            raw_temp = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip())
            temp_info = f"{round(raw_temp / 1000, 1)} °C"
    except Exception:
        pass

    return {
        "model": model,
        "os": f"CasaOS ({platform.system()})",
        "arch": platform.machine() or "aarch64",
        "ram": ram_info,
        "cpu": temp_info
    }

@app.get("/api/v1/config")
def get_config():
    return load_config()

@app.post("/api/v1/config")
def save_config(config: ConfigModel):
    data = config.dict()
    save_config_file(data)
    return {"status": "success", "config": data}

@app.post("/api/v1/config/test-telegram")
def test_telegram(data: TelegramTestModel):
    token = (data.telegram_token or data.token).strip()
    chat_id = (data.telegram_chat_id or data.chat_id).strip()

    if not token or not chat_id:
        cfg = load_config()
        token = token or cfg.get("telegram_token", "").strip()
        chat_id = chat_id or cfg.get("telegram_chat_id", "").strip()

    if not token or not chat_id:
        raise HTTPException(status_code=400, detail="Faltan credenciales (Token o Chat ID)")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🧪 *CasaOS Backup Manager*: Mensaje de prueba exitoso.",
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=8)
        res_data = res.json()
        
        if res.status_code == 200 and res_data.get("ok"):
            return {"status": "ok", "message": "Mensaje enviado con éxito"}
            
        error_desc = res_data.get("description", "Error desconocido de Telegram")
        logger.error(f"Error Telegram API ({res.status_code}): {error_desc}")
        raise HTTPException(status_code=400, detail=f"Telegram API: {error_desc}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error de conexión con Telegram: {e}")
        raise HTTPException(status_code=500, detail=f"Error de conexión: {str(e)}")

# --- ENDPOINTS DE APPS Y DOCKER ---
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

def get_all_mounts():
    disks = disk_service.get_disks()
    return [d["mountpoint"] for d in disks if "mountpoint" in d]

@app.get("/api/v1/system/disks")
def get_disks():
    return {"disks": disk_service.get_disks()}

# --- PROCESOS DE RESPALDO Y RESTAURACIÓN ---
def perform_real_backup(app_name: str, target_disk: str, job_id: str):
    start = time.time()
    active_jobs[job_id] = {"status": "running", "progress": 5, "message": "Iniciando comprobaciones...", "cancelled": False}

    cfg = load_config()
    if not target_disk:
        target_disk = cfg.get("target_disk", "")

    real_target = None
    if target_disk:
        clean_target = target_disk[5:] if target_disk.startswith("/host/") else target_disk
        for cand in [clean_target, f"/host{clean_target}"]:
            if os.path.exists(cand):
                real_target = cand
                break

    if not real_target:
        cfg_disk = cfg.get("target_disk")
        if cfg_disk and os.path.exists(cfg_disk):
            real_target = cfg_disk
        else:
            real_target = "/DATA/Backups" if os.path.exists("/DATA/Backups") else "/host/DATA/Backups"

    if real_target.endswith("Backups"):
        base_backups_dir = Path(real_target)
    else:
        base_backups_dir = Path(real_target) / "Backups"

    normalized_app = app_name.replace("_", " ").strip().lower()

    if normalized_app in ["sistema completo", "casaos completo", "disaster recovery"]:
        active_jobs[job_id]["message"] = "Conectando con motor Duplicati..."
        active_jobs[job_id]["progress"] = 10

        dup_url = cfg.get("duplicati_url", "http://172.17.0.1:8200")
        dup_password = cfg.get("duplicati_password", "")

        dup_job_id = duplicati_orchestrator.find_job_id_by_name(app_name, dup_url, dup_password)

        orchestration_res = duplicati_orchestrator.run_full_disaster_recovery(
            app_name=app_name,
            target_disk_path=str(base_backups_dir),
            duplicati_job_id=dup_job_id,
            duplicati_url=dup_url,
            duplicati_password=dup_password
        )

        if not orchestration_res.get("success"):
            raw_err = str(orchestration_res.get('errors') or orchestration_res.get('error') or '')
            if "401" in raw_err or "Failed to log in" in raw_err:
                err_msg = "Error de autenticación (401): Revisa la contraseña de Duplicati en ⚙️ Configuración."
            else:
                err_msg = f"Error al iniciar en Duplicati: {raw_err}"

            active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}
            
            with get_db() as conn:
                conn.cursor().execute(
                    "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    ("Backup", app_name, "failed", round(time.time() - start, 2), err_msg, int(time.time() * 1000))
                )
                conn.commit()
            send_telegram_notification(f"❌ *Copia fallida en Duplicati*: {app_name}\n{err_msg}")
            return

        active_jobs[job_id]["message"] = "Esperando inicio de proceso en Duplicati..."
        time.sleep(2)

        was_running = False
        idle_counter = 0

        while True:
            if active_jobs[job_id].get("cancelled"):
                kill_rsync_processes()

                inc_dir = base_backups_dir / "DisasterRecovery" / f"incremental_{app_name}"
                if inc_dir.exists():
                    try:
                        shutil.rmtree(inc_dir, ignore_errors=True)
                        logger.info(f"[ROLLBACK] Eliminada copia cancelada: {inc_dir}")
                    except Exception as rm_err:
                        logger.error(f"[ROLLBACK ERROR] No se pudo borrar {inc_dir}: {rm_err}")

                elapsed = round(time.time() - start, 2)
                active_jobs[job_id] = {"status": "cancelled", "progress": 0, "message": "Proceso cancelado por el usuario"}

                with get_db() as conn:
                    conn.cursor().execute(
                        "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        ("Backup", app_name, "cancelled", elapsed, "Cancelado por el usuario", int(time.time() * 1000))
                    )
                    conn.commit()

                send_telegram_notification(f"⚠️ *Copia cancelada por el usuario*: {app_name}")
                return

            status_info = duplicati_orchestrator.get_task_status(
                task_id=dup_job_id, 
                duplicati_url=dup_url,
                duplicati_password=dup_password
            )
            
            phase = status_info.get("phase", "Idle")
            status = status_info.get("status")
            progress = status_info.get("progress", 0.0)

            if status == "running":
                was_running = True
                idle_counter = 0
                active_jobs[job_id]["progress"] = max(15, min(99, int(progress)))
                active_jobs[job_id]["message"] = f"Duplicati: {phase} ({round(progress, 1)}%)"
            
            elif status == "completed":
                break

            elif status == "idle":
                if was_running:
                    break
                else:
                    idle_counter += 1
                    if idle_counter > 5:
                        err_msg = f"Duplicati no inició el trabajo '{app_name}' (ID: {dup_job_id}). Revisa la app nativa."
                        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}
                        with get_db() as conn:
                            conn.cursor().execute(
                                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                                ("Backup", app_name, "failed", round(time.time() - start, 2), err_msg, int(time.time() * 1000))
                            )
                            conn.commit()
                        send_telegram_notification(f"❌ *Copia fallida en Duplicati*: {app_name}\n{err_msg}")
                        return
                    active_jobs[job_id]["message"] = f"Iniciando tarea en Duplicati ({idle_counter}/5)..."

            elif status in ["error", "unknown"]:
                err_msg = f"Error reportado por Duplicati ({phase})"
                active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}
                with get_db() as conn:
                    conn.cursor().execute(
                        "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        ("Backup", app_name, "failed", round(time.time() - start, 2), err_msg, int(time.time() * 1000))
                    )
                    conn.commit()
                send_telegram_notification(f"❌ *Copia fallida en Duplicati*: {app_name}\n{err_msg}")
                return

            time.sleep(3)

        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "success", "progress": 100, "message": "Copia de seguridad incremental completada en Duplicati"}

        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup (Duplicati)", app_name, "success", elapsed, "Duplicati Backup OK", int(time.time() * 1000))
            )
            conn.commit()

        send_telegram_notification(f"✅ *Copia de Sistema Completo finalizada*: {app_name}\nMotor: `Duplicati`\nDuración: {elapsed}s")
        return

    dest_dir = base_backups_dir / "Apps" / app_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{app_name.lower()}_backup_{timestamp}.tar.gz"
    dest_file = dest_dir / filename
    src_dir = Path(f"/DATA/AppData/{app_name}")

    try:
        if not src_dir.exists():
            active_jobs[job_id] = {"status": "failed", "progress": 100, "message": f"Origen {src_dir} no existe"}
            send_telegram_notification(f"❌ *Copia fallida*: {app_name}\nOrigen `{src_dir}` no existe.")
            return

        active_jobs[job_id]["message"] = "Verificando espacio libre en disco..."
        active_jobs[job_id]["progress"] = 15

        required_bytes = 0
        for root, _, files in os.walk(src_dir):
            for f in files:
                fp = os.path.join(root, f)
                if os.path.exists(fp):
                    try:
                        required_bytes += os.path.getsize(fp)
                    except OSError:
                        pass

        dest_usage = shutil.disk_usage(dest_dir)
        free_bytes = dest_usage.free
        margin_bytes = 100 * 1024 * 1024

        if free_bytes < (required_bytes + margin_bytes):
            req_mb = round(required_bytes / (1024 * 1024), 2)
            free_mb = round(free_bytes / (1024 * 1024), 2)
            err_msg = f"Espacio insuficiente. Necesario: ~{req_mb} MB, Libre: {free_mb} MB"
            
            active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}
            
            with get_db() as conn:
                conn.cursor().execute(
                    "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    ("Backup", app_name, "failed", round(time.time() - start, 2), err_msg, int(time.time() * 1000))
                )
                conn.commit()

            send_telegram_notification(f"⚠️ *Copia abortada (Sin espacio)*: {app_name}\nSe requieren ~{req_mb} MB y solo hay {free_mb} MB libres.")
            return

        active_jobs[job_id]["progress"] = 35
        active_jobs[job_id]["message"] = f"Comprimiendo {src_dir.name}..."

        was_cancelled = False
        with tarfile.open(dest_file, "w:gz") as tar:
            for root, _, files in os.walk(src_dir):
                for f in files:
                    if active_jobs[job_id].get("cancelled"):
                        was_cancelled = True
                        break
                    fp = os.path.join(root, f)
                    tar.add(fp, arcname=os.path.relpath(fp, src_dir))
                if was_cancelled:
                    break

        if was_cancelled:
            if dest_file.exists():
                try:
                    os.remove(dest_file)
                except Exception as rm_err:
                    logger.error(f"[CANCELATION ERROR] No se pudo borrar {dest_file}: {rm_err}")
            
            elapsed = round(time.time() - start, 2)
            active_jobs[job_id] = {"status": "cancelled", "progress": 0, "message": "Proceso cancelado por el usuario"}
            
            with get_db() as conn:
                conn.cursor().execute(
                    "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    ("Backup", app_name, "cancelled", elapsed, "Cancelado por el usuario", int(time.time() * 1000))
                )
                conn.commit()

            send_telegram_notification(f"⚠️ *Copia cancelada*: {app_name}")
            return

        list_backups(max_keep_per_app=3)

        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "success", "progress": 100, "message": "Copia completada con éxito", "file": filename}

        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup", app_name, "success", elapsed, filename, int(time.time() * 1000))
            )
            conn.commit()

        send_telegram_notification(f"✅ *Copia finalizada*: {app_name}\nArchivo: `{filename}`\nDuración: {elapsed}s")

    except Exception as e:
        if dest_file.exists():
            try:
                os.remove(dest_file)
                logger.info(f"[ROLLBACK] Archivo incompleto eliminado: {dest_file}")
            except Exception as rm_err:
                logger.error(f"[ROLLBACK ERROR] No se pudo eliminar {dest_file}: {rm_err}")

        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": str(e)}
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup", app_name, "failed", elapsed, str(e), int(time.time() * 1000))
            )
            conn.commit()
            
        send_telegram_notification(f"❌ *Error en copia*: {app_name}\nDetalle: {str(e)}")

def perform_real_restore(filename: str, job_id: str):
    start = time.time()
    active_jobs[job_id] = {"status": "running", "progress": 10, "message": "Buscando copia de seguridad...", "cancelled": False}

    search_paths = set()
    if os.path.exists("/DATA/Backups"):
        search_paths.add("/DATA/Backups")
    if os.path.exists("/host/DATA/Backups"):
        search_paths.add("/host/DATA/Backups")

    for mount in get_all_mounts():
        clean_mount = mount[5:] if mount.startswith("/host/") else mount
        cand_rw = os.path.join(clean_mount, "Backups") if not clean_mount.endswith("Backups") else clean_mount
        cand_ro = os.path.join("/host" + clean_mount, "Backups") if not clean_mount.endswith("Backups") else f"/host{clean_mount}"
        if os.path.exists(cand_rw): search_paths.add(cand_rw)
        elif os.path.exists(cand_ro): search_paths.add(cand_ro)

    target_file = None
    for base in search_paths:
        for root, _, files in os.walk(base):
            if filename in files:
                target_file = Path(root) / filename
                break
        if target_file:
            break

    if not target_file or not target_file.exists():
        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": f"Archivo {filename} no encontrado."}
        send_telegram_notification(f"❌ *Restauración fallida*: Archivo `{filename}` no encontrado.")
        return

    try:
        fn_lower = filename.lower()
        if "_backup_" in fn_lower:
            app_key = fn_lower.split("_backup_")[0]
        elif fn_lower.startswith("disaster_recovery_") or fn_lower.startswith("full_system_"):
            app_key = "sistema_completo"
        else:
            app_key = fn_lower.split(".")[0]

        dest_dir = Path("/DATA/AppData") if app_key in ["sistema_completo", "disaster_recovery"] else Path(f"/DATA/AppData/{app_key}")
        dest_dir.mkdir(parents=True, exist_ok=True)

        active_jobs[job_id]["progress"] = 40
        active_jobs[job_id]["message"] = f"Descomprimiendo en {dest_dir}..."

        with tarfile.open(target_file, "r:gz") as tar:
            if hasattr(tarfile, 'data_filter'):
                tar.extractall(path=dest_dir, filter='data')
            else:
                tar.extractall(path=dest_dir)

        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "success", "progress": 100, "message": "Restauración completada con éxito", "file": filename}

        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Restore", app_key.capitalize(), "success", elapsed, filename, int(time.time() * 1000))
            )
            conn.commit()

        send_telegram_notification(f"🔄 *Restauración completada*: {app_key.capitalize()}\nArchivo: `{filename}`")

    except Exception as e:
        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": str(e)}
        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Restore", filename, "failed", elapsed, str(e), int(time.time() * 1000))
            )
            conn.commit()

        send_telegram_notification(f"❌ *Error al restaurar*: {filename}\nDetalle: {str(e)}")

# --- RUTAS DE EJECUCIÓN Y TAREAS ---
@app.post("/api/v1/backups/run-app/{app_name}")
def run_backup(app_name: str, background_tasks: BackgroundTasks, target_disk: str = Query(None)):
    job_id = f"job_{app_name}_{int(time.time())}"
    background_tasks.add_task(perform_real_backup, app_name, target_disk or "", job_id)
    return {"status": "started", "job_id": job_id}

@app.post("/api/v1/backups/run-system")
def run_system_backup(background_tasks: BackgroundTasks, target_disk: str = Query(None)):
    job_id = f"job_Sistema_Completo_{int(time.time())}"
    background_tasks.add_task(perform_real_backup, "Sistema_Completo", target_disk or "", job_id)
    return {"status": "started", "job_id": job_id}

@app.post("/api/v1/backups/restore/{filename}")
@app.post("/api/v1/backups/restore")
def restore_backup(filename: str, background_tasks: BackgroundTasks):
    job_id = f"job_restore_{int(time.time())}"
    background_tasks.add_task(perform_real_restore, filename, job_id)
    return {"status": "started", "job_id": job_id}

@app.get("/api/v1/backups/job-status/{job_id}")
def get_job_status(job_id: str):
    return active_jobs.get(job_id, {"status": "unknown", "progress": 0, "message": "Iniciando..."})

@app.post("/api/v1/backups/job-cancel/{job_id}")
@app.post("/api/v1/backups/cancel/{job_id}")
def cancel_job(job_id: str):
    if job_id in active_jobs:
        active_jobs[job_id]["cancelled"] = True
        kill_rsync_processes()
        return {"status": "cancelled"}
    return {"status": "not_found"}

@app.get("/api/v1/backups/list")
@app.get("/api/v1/backups")
def list_backups(max_keep_per_app: int = 3):
    search_paths = set()

    if os.path.exists("/DATA/Backups"):
        search_paths.add("/DATA/Backups")
    elif os.path.exists("/host/DATA/Backups"):
        search_paths.add("/host/DATA/Backups")

    for mount in get_all_mounts():
        clean_mount = mount[5:] if mount.startswith("/host/") else mount
        cand_rw = os.path.join(clean_mount, "Backups") if not clean_mount.endswith("Backups") else clean_mount
        cand_ro = os.path.join("/host" + clean_mount, "Backups") if not clean_mount.endswith("Backups") else f"/host{clean_mount}"
        
        if os.path.exists(cand_rw):
            search_paths.add(cand_rw)
        elif os.path.exists(cand_ro):
            search_paths.add(cand_ro)

    app_groups = {}
    seen_files = set()

    for base_path in search_paths:
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.startswith(".") or file.startswith("._"):
                    continue
                
                fn_lower = file.lower()
                if fn_lower.startswith("duplicati-") or "dblock" in fn_lower or "dindex" in fn_lower or "dlist" in fn_lower:
                    continue
                
                if fn_lower.endswith((".tar.gz", ".tgz", ".zip")):
                    fp = os.path.join(root, file)
                    try:
                        real_path = os.path.realpath(fp)
                        if real_path in seen_files:
                            continue
                        seen_files.add(real_path)

                        stats = os.stat(fp)
                        
                        if "_backup_" in fn_lower:
                            app_key = fn_lower.split("_backup_")[0]
                        elif fn_lower.startswith("disaster_recovery_") or fn_lower.startswith("full_system_"):
                            app_key = "disaster_recovery"
                        else:
                            parent_name = os.path.basename(root).lower()
                            if parent_name and parent_name not in ("backups", "apps", "casaos"):
                                app_key = parent_name
                            else:
                                app_key = fn_lower.split(".")[0].split("_")[0]

                        if app_key not in app_groups:
                            app_groups[app_key] = []

                        app_groups[app_key].append({
                            "filename": file,
                            "filepath": fp,
                            "app_name": app_key.capitalize(),
                            "timestamp": stats.st_mtime,
                            "size": stats.st_size
                        })
                    except Exception as e:
                        logger.error(f"Error metadatos en {fp}: {e}")

    retained_backups = []

    for app_key, entries in app_groups.items():
        entries.sort(key=lambda x: x["timestamp"], reverse=True)

        to_keep = entries[:max_keep_per_app]
        to_delete = entries[max_keep_per_app:]

        for old in to_delete:
            try:
                if os.path.exists(old["filepath"]):
                    os.remove(old["filepath"])
                    logger.info(f"[RETENCION] Eliminado del disco: {old['filepath']}")
            except Exception as e:
                logger.error(f"[ERROR] No se pudo borrar {old['filepath']}: {e}")

        for item in to_keep:
            dt = datetime.fromtimestamp(item["timestamp"])
            sz = item["size"]
            size_mb = round(sz / (1024 * 1024), 2)
            size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(sz / 1024, 1)} KB"

            retained_backups.append({
                "filename": item["filename"],
                "app_name": item["app_name"],
                "app": item["app_name"],
                "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "size_str": size_str,
                "timestamp": item["timestamp"]
            })

    retained_backups.sort(key=lambda x: (x["app_name"].lower(), -x["timestamp"]))
    return {"backups": retained_backups}

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

@app.delete("/api/v1/executions")
@app.delete("/api/v1/logs")
def clear_logs():
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM execution_logs")
        conn.commit()
    return {"status": "ok"}