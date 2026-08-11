import asyncio
import logging
from sqlalchemy.orm import Session
from app.schemas.execution import ExecutionStatus, ExecutionUpdate
from app.services.execution_history_service import ExecutionHistoryService
from app.services.backup_engine_service import BackupEngineService  # Ajusta según la importación de tu motor

logger = logging.getLogger(__name__)


class BackgroundWorkerService:
    @staticmethod
    async def run_backup_job_async(
        execution_id: str,
        db_factory,  # Callable para obtener una sesión fresca de BD en el hilo en segundo plano
        backup_engine_service: BackupEngineService
    ):
        """Ejecuta el trabajo de copia en segundo plano y actualiza el historial."""
        db: Session = db_factory()
        history_service = ExecutionHistoryService(db)

        try:
            # 1. Marcar como RUNNING
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(status=ExecutionStatus.RUNNING, progress_percentage=10)
            )

            # 2. Recuperar el registro para obtener los detalles del job/app
            record = history_service.get_execution(execution_id)
            if not record:
                logger.error(f"Ejecución {execution_id} no encontrada en la base de datos.")
                return

            # 3. Invocar al motor de backup real (Duplicati)
            # Adaptar según el método exacto de tu BackupEngineService
            result = await backup_engine_service.execute_backup(
                app_name=record.app_name,
                destination_path=record.destination_path,
                backend_type=record.backend_type
            )

            # 4. Actualizar estado a SUCCESS
            history_service.update_execution(
                execution_id,
                ExecutionUpdate(
                    status=ExecutionStatus.SUCCESS,
                    progress_percentage=100,
                    execution_reference=result.get("execution_reference")
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