import asyncio
import logging
from sqlalchemy.orm import Session

from app.schemas.execution import ExecutionStatus, ExecutionUpdate
from app.services.execution_history_service import ExecutionHistoryService

logger = logging.getLogger(__name__)


class BackgroundWorkerService:
    @staticmethod
    async def run_backup_job_async(
        execution_id: str,
        db_factory
    ):
        """Ejecuta el trabajo de copia en segundo plano actualizando el estado y progreso en SQLite."""
        db: Session = db_factory()
        history_service = ExecutionHistoryService(db)

        try:
            # 1. Marcar estado como RUNNING
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(status=ExecutionStatus.RUNNING, progress_percentage=15)
            )

            # 2. Recuperar el registro
            record = history_service.get_execution(execution_id)
            if not record:
                logger.error(f"Ejecución {execution_id} no encontrada en la base de datos.")
                return

            # 3. Simulación de avance incremental del trabajo en segundo plano
            await asyncio.sleep(1.5)
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(status=ExecutionStatus.RUNNING, progress_percentage=50)
            )

            await asyncio.sleep(1.5)
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(status=ExecutionStatus.RUNNING, progress_percentage=85)
            )

            await asyncio.sleep(1)

            # 4. Marcar como SUCCESS
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(
                    status=ExecutionStatus.SUCCESS,
                    progress_percentage=100,
                    execution_reference=f"REF-{record.app_name.upper()}-OK"
                )
            )
            logger.info(f"Copia de seguridad completada con éxito para execution_id: {execution_id}")

        except Exception as e:
            logger.exception(f"Error durante la ejecución en segundo plano: {str(e)}")
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(
                    status=ExecutionStatus.FAILED,
                    error_message=str(e)
                )
            )
        finally:
            db.close()