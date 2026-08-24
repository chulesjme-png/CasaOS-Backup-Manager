from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.execution import ExecutionRecordModel
from app.schemas.execution import ExecutionCreate, ExecutionUpdate, ExecutionStatus


class ExecutionHistoryService:
    def __init__(self, db: Session):
        self.db = db

    def create_execution(self, data: ExecutionCreate) -> ExecutionRecordModel:
        record = ExecutionRecordModel(
            app_name=data.app_name,
            job_id=data.job_id,
            backend_type=data.backend_type,
            destination_path=data.destination_path,
            status=ExecutionStatus.PENDING,
            progress_percentage=0,
            start_time=datetime.utcnow()
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_execution(self, execution_id: str, data: ExecutionUpdate) -> Optional[ExecutionRecordModel]:
        record = self.db.query(ExecutionRecordModel).filter(ExecutionRecordModel.id == execution_id).first()
        if not record:
            return None

        if data.status is not None:
            record.status = data.status
            if data.status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
                record.end_time = datetime.utcnow()

        if data.progress_percentage is not None:
            record.progress_percentage = data.progress_percentage

        if data.error_message is not None:
            record.error_message = data.error_message

        if data.execution_reference is not None:
            record.execution_reference = data.execution_reference

        self.db.commit()
        self.db.refresh(record)
        return record

    def get_execution(self, execution_id: str) -> Optional[ExecutionRecordModel]:
        return self.db.query(ExecutionRecordModel).filter(ExecutionRecordModel.id == execution_id).first()

    def list_executions(self, limit: int = 50, backend_type: Optional[str] = None) -> List[ExecutionRecordModel]:
        """Obtiene la lista de ejecuciones, permitiendo filtrar por backend opcionalmente."""
        query = self.db.query(ExecutionRecordModel)
        
        if backend_type:
            query = query.filter(ExecutionRecordModel.backend_type == backend_type)
            
        return (
            query
            .order_by(ExecutionRecordModel.start_time.desc())
            .limit(limit)
            .all()
        )