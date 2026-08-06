import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.routers.api_schedules import load_schedules
from app.routers.api_executions import run_disaster_recovery_backup

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def trigger_scheduled_backup(task_id: str, target_app: str, backend: str):
    """Ejecuta la tarea de respaldo invocada por el programador."""
    logger.info(f"⏰ [SCHEDULER] Iniciando tarea programada: {task_id} ({target_app}) en backend: {backend}")
    try:
        # Ejecuta la lógica de copia de seguridad registrada en api_executions
        res = run_disaster_recovery_backup()
        logger.info(f"✅ [SCHEDULER] Tarea {task_id} finalizada con éxito: {res}")
    except Exception as e:
        logger.error(f"❌ [SCHEDULER] Error ejecutando la tarea programada {task_id}: {str(e)}")


def sync_scheduler_jobs():
    """Lee el archivo JSON de configuración y sincroniza los trabajos en el motor APScheduler."""
    scheduler.remove_all_jobs()
    tasks = load_schedules()

    for task in tasks:
        if not task.get("enabled", False):
            continue

        task_id = task.get("id")
        time_str = task.get("time", "03:00")
        try:
            hour, minute = time_str.split(":")
        except ValueError:
            hour, minute = "03", "00"

        # Configurar frecuencia semanal o diaria
        frequency = task.get("frequency", "daily")
        days = task.get("days_of_week", [0, 1, 2, 3, 4, 5, 6])
        
        if frequency == "weekly":
            day_of_week_str = ",".join(str(d) for d in days)
            trigger = CronTrigger(hour=int(hour), minute=int(minute), day_of_week=day_of_week_str)
        else:
            trigger = CronTrigger(hour=int(hour), minute=int(minute))

        scheduler.add_job(
            trigger_scheduled_backup,
            trigger,
            id=task_id,
            args=[task_id, task.get("target_app"), task.get("backend")],
            replace_existing=True
        )
        logger.info(f"📅 [SCHEDULER] Tarea '{task.get('name')}' programada a las {time_str} hrs.")


def start_scheduler():
    """Inicia el motor en segundo plano."""
    if not scheduler.running:
        scheduler.start()
        sync_scheduler_jobs()
        logger.info("🚀 [SCHEDULER] Motor de tareas en segundo plano iniciado.")


def stop_scheduler():
    """Detiene el motor en segundo plano."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 [SCHEDULER] Motor de tareas detenido.")