import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.duplicati_service import duplicati_service

logger = logging.getLogger("casaos-backup")

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False

    def start(self):
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("[SchedulerService] Planificador de tareas iniciado correctamente.")
            
            # Programar Disaster Recovery diario por defecto a las 03:00 AM
            self.schedule_daily_disaster_recovery(hour=3, minute=0)

    def schedule_daily_disaster_recovery(self, hour: int = 3, minute: int = 0):
        # Evitar duplicados
        job_id = "daily_disaster_recovery"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        self.scheduler.add_job(
            duplicati_service.run_full_disaster_recovery,
            trigger=CronTrigger(hour=hour, minute=minute),
            id=job_id,
            name="Respaldo Diario Disaster Recovery",
            replace_existing=True
        )
        logger.info(f"[SchedulerService] Disaster Recovery programado diariamente a las {hour:02d}:{minute:02d}")

    def get_scheduled_jobs(self):
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": str(job.next_run_time) if job.next_run_time else "Desconocido"
            })
        return jobs

    def shutdown(self):
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False

scheduler_service = SchedulerService()