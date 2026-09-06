import os
import time
import shutil
import logging
import subprocess
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("casaos-backup")

def perform_real_backup(app_name: str, target_disk: str, job_id: str):
    start = time.time()
    active_jobs[job_id] = {
        "status": "running",
        "progress": 5,
        "message": "Iniciando comprobaciones...",
        "cancelled": False
    }

    normalized_app = app_name.replace("_", " ").strip().lower()
    is_system_backup = normalized_app in ["sistema completo", "casaos completo", "disaster recovery"]

    # 1. Definir origen
    if is_system_backup:
        src_dir = Path("/DATA")
        category = "System"
        clean_app_name = "Sistema_Completo"
    else:
        src_dir = Path(f"/DATA/AppData/{app_name}")
        category = "Apps"
        clean_app_name = app_name

    if not src_dir.exists():
        err_msg = f"El directorio origen '{src_dir}' no existe."
        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}
        send_telegram_notification(f"❌ *Copia fallida*: {clean_app_name}\nOrigen `{src_dir}` no existe.")
        return

    # 2. Definir destino obligatoriamente dentro de /BackUps/
    real_target = None
    if target_disk:
        clean_target = target_disk[5:] if target_disk.startswith("/host/") else target_disk
        for cand in [clean_target, f"/host{clean_target}"]:
            if os.path.exists(cand):
                real_target = cand
                break

    if not real_target:
        cfg = load_config()
        cfg_disk = cfg.get("target_disk")
        if cfg_disk and os.path.exists(cfg_disk):
            real_target = cfg_disk
        else:
            real_target = "/DATA"

    base_dest_dir = Path(real_target) / "BackUps" / category / clean_app_name
    base_dest_dir.mkdir(parents=True, exist_ok=True)

    # Definir rutas temporales, de enlace previo y final
    tmp_dir = base_dest_dir / ".tmp_backup"
    latest_link = base_dest_dir / "latest"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_dir = base_dest_dir / f"backup_{timestamp}"

    # Limpieza preventiva de temporales colgados
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)

    active_jobs[job_id]["message"] = "Verificando espacio en disco..."
    active_jobs[job_id]["progress"] = 10

    # 3. Comprobar espacio libre
    try:
        dest_usage = shutil.disk_usage(base_dest_dir)
        if dest_usage.free < (500 * 1024 * 1024):  # Margen mínimo de 500 MB
            err_msg = "Espacio insuficiente en el disco de destino."
            active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}
            send_telegram_notification(f"⚠️ *Copia abortada*: {clean_app_name}\n{err_msg}")
            return
    except Exception as e:
        logger.warning(f"No se pudo verificar el espacio en disco: {e}")

    active_jobs[job_id]["message"] = "Ejecutando rsync incremental..."
    active_jobs[job_id]["progress"] = 25

    # 4. Construcción del comando rsync incremental con enlaces duros
    rsync_cmd = ["rsync", "-aHAX", "--delete"]

    # Si existe una copia previa ('latest'), usamos enlaces duros para lograr incremento ultrarrápido
    if latest_link.exists():
        resolved_latest = latest_link.resolve()
        rsync_cmd.append(f"--link-dest={resolved_latest}")

    rsync_cmd.extend([f"{src_dir}/", f"{tmp_dir}/"])

    process = None
    try:
        process = subprocess.Popen(rsync_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Monitor de cancelación y progreso simulado
        while process.poll() is None:
            if active_jobs[job_id].get("cancelled"):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

                # ROLLBACK: Eliminación de archivos temporales incompletos
                if tmp_dir.exists():
                    shutil.rmtree(tmp_dir, ignore_errors=True)

                active_jobs[job_id] = {"status": "cancelled", "progress": 0, "message": "Proceso cancelado por el usuario"}
                send_telegram_notification(f"⚠️ *Copia cancelada*: {clean_app_name}")
                return

            time.sleep(1)

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(f"rsync falló con código {process.returncode}: {stderr.strip()}")

        # 5. Finalización atómica: Renombrado y actualización del enlace 'latest'
        active_jobs[job_id]["message"] = "Verificando y consolidando copia..."
        active_jobs[job_id]["progress"] = 90

        # Renombrar carpeta temporal a nombre final
        os.rename(tmp_dir, final_dir)

        # Actualizar enlace simbólico 'latest' al último backup completado
        if latest_link.is_symlink() or latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(final_dir.name, target_is_directory=True)

        # 6. Política de retención: Mantener solo las últimas 3 copias por app
        all_backups = sorted(
            [d for d in base_dest_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
            key=lambda x: x.name,
            reverse=True
        )
        for old_backup in all_backups[3:]:
            shutil.rmtree(old_backup, ignore_errors=True)
            logger.info(f"[RETENCIÓN] Eliminada copia antigua: {old_backup}")

        elapsed = round(time.time() - start, 2)
        active_jobs[job_id] = {
            "status": "success",
            "progress": 100,
            "message": f"Copia incremental completada con éxito en {elapsed}s",
            "folder": final_dir.name
        }

        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup Incremental", clean_app_name, "success", elapsed, final_dir.name, int(time.time() * 1000))
            )
            conn.commit()

        send_telegram_notification(
            f"✅ *Copia Incremental Finalizada*: {clean_app_name}\n"
            f"Carpeta: `{final_dir.name}`\n"
            f"Ubicación: `/BackUps/{category}/{clean_app_name}`\n"
            f"Duración: {elapsed}s"
        )

    except Exception as e:
        # ROLLBACK GARANTIZADO: Borrado completo si hay cualquier fallo
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.info(f"[ROLLBACK] Carpeta temporal eliminada por error: {tmp_dir}")

        elapsed = round(time.time() - start, 2)
        err_msg = str(e)
        active_jobs[job_id] = {"status": "failed", "progress": 100, "message": err_msg}

        with get_db() as conn:
            conn.cursor().execute(
                "INSERT INTO execution_logs (job_type, target_name, status, duration_seconds, message, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                ("Backup Incremental", clean_app_name, "failed", elapsed, err_msg, int(time.time() * 1000))
            )
            conn.commit()

        send_telegram_notification(f"❌ *Error en copia incremental*: {clean_app_name}\nDetalle: `{err_msg}`")


@app.get("/api/v1/backups/list")
@app.get("/api/v1/backups")
def list_backups(max_keep_per_app: int = 3):
    search_paths = set()

    for mount in get_all_mounts():
        clean_mount = mount[5:] if mount.startswith("/host/") else mount
        cand_rw = os.path.join(clean_mount, "BackUps")
        cand_ro = os.path.join("/host" + clean_mount, "BackUps")
        
        if os.path.exists(cand_rw):
            search_paths.add(cand_rw)
        elif os.path.exists(cand_ro):
            search_paths.add(cand_ro)

    if os.path.exists("/DATA/BackUps"):
        search_paths.add("/DATA/BackUps")

    retained_backups = []

    for base_path in search_paths:
        base_p = Path(base_path)
        for category_dir in [base_p / "Apps", base_p / "System"]:
            if not category_dir.exists():
                continue

            for app_dir in category_dir.iterdir():
                if not app_dir.is_dir():
                    continue

                app_name = app_dir.name
                backup_folders = sorted(
                    [d for d in app_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
                    key=lambda x: x.name,
                    reverse=True
                )

                for backup_folder in backup_folders[:max_keep_per_app]:
                    stats = backup_folder.stat()
                    dt = datetime.fromtimestamp(stats.st_mtime)

                    # Calcular tamaño real del directorio
                    total_size = sum(
                        f.stat().st_size for f in backup_folder.glob("**/*") if f.is_file() and not f.is_symlink()
                    )
                    size_mb = round(total_size / (1024 * 1024), 2)
                    size_str = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(total_size / 1024, 1)} KB"

                    retained_backups.append({
                        "filename": backup_folder.name,
                        "app_name": app_name.capitalize(),
                        "app": app_name.capitalize(),
                        "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "size_str": size_str,
                        "timestamp": stats.st_mtime,
                        "path": str(backup_folder)
                    })

    retained_backups.sort(key=lambda x: (x["app_name"].lower(), -x["timestamp"]))
    return {"backups": retained_backups}