import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database.connection import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def _execute_scheduled_backup(app_name: str, destination_path: str):
    """Callback invocado automáticamente por APScheduler cuando se cumple la regla cron."""
    from app.routers.api_executions import run_backup_task
    from app.models.execution import ExecutionRecordModel

    logger.info(f"⏰ Ejecutando tarea programada automática para: {app_name}")
    
    db = SessionLocal()
    try:
        execution = ExecutionRecordModel(
            app_name=app_name,
            backend_type="duplicati",
            destination_path=destination_path,
            status="PENDING",
            progress_percentage=0
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # Ejecución del worker
        run_backup_task(
            execution_id=execution.id,
            app_name=app_name,
            destination_path=destination_path,
            db=db
        )
    except Exception as e:
        logger.error(f"Error al ejecutar backup programado de {app_name}: {e}")
    finally:
        db.close()


def start_scheduler():
    """Inicia el motor APScheduler si no estaba activo."""
    if not scheduler.running:
        scheduler.start()
        logger.info("🚀 APScheduler iniciado correctamente.")


def stop_scheduler():
    """Detiene el motor APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 APScheduler detenido.")


def add_cron_job(job_id: str, app_name: str, cron_expression: str, destination_path: str):
    """Añade o reemplaza un trabajo Cron en el motor de agendamiento."""
    try:
        trigger = CronTrigger.from_crontab(cron_expression)
        scheduler.add_job(
            _execute_scheduled_backup,
            trigger=trigger,
            id=job_id,
            args=[app_name, destination_path],
            replace_existing=True
        )
        logger.info(f"📅 Tarea agregada a APScheduler: [{job_id}] {app_name} con regla '{cron_expression}'")
    except Exception as e:
        logger.error(f"Error parseando expresión cron '{cron_expression}': {e}")


def remove_cron_job(job_id: str):
    """Elimina un trabajo programado del motor."""
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"🗑️ Tarea eliminada de APScheduler: [{job_id}]")