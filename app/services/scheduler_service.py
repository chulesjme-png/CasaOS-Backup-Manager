import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import config_manager
from app.services.duplicati_service import duplicati_service

logger = logging.getLogger("casaos-backup")

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.job_id = "scheduled_disaster_recovery"

    def start(self):
        """Inicia el planificador de fondo y configura la tarea guardada."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("[Scheduler] Planificador de tareas iniciado.")
            self.reload_schedule()

    def reload_schedule(self):
        """Recarga la programación desde la configuración guardada."""
        config = config_manager.config
        
        # Eliminar trabajo previo si existe
        if self.scheduler.get_job(self.job_id):
            self.scheduler.remove_job(self.job_id)

        try:
            time_parts = config.schedule_time.split(":")
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0

            trigger = None
            if config.schedule_frequency == "daily":
                trigger = CronTrigger(hour=hour, minute=minute)
            elif config.schedule_frequency == "weekly":
                trigger = CronTrigger(day_of_week="sun", hour=hour, minute=minute)
            elif config.schedule_frequency == "monthly":
                trigger = CronTrigger(day=1, hour=hour, minute=minute)

            if trigger:
                self.scheduler.add_job(
                    func=duplicati_service.run_full_disaster_recovery,
                    trigger=trigger,
                    id=self.job_id,
                    replace_existing=True
                )
                logger.info(f"[Scheduler] Backup automático programado ({config.schedule_frequency}) a las {config.schedule_time}")
            else:
                logger.info("[Scheduler] Programación deshabilitada o frecuencia no reconocida.")
        except Exception as e:
            logger.error(f"[Scheduler] Error al programar la tarea: {e}")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("[Scheduler] Planificador detenido.")

scheduler_service = SchedulerService()