import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum

# Corrección de importación: apunta al conector de base de datos de la app
from app.database.connection import Base
from app.schemas.execution import ExecutionStatus


class ExecutionRecordModel(Base):
    __tablename__ = "execution_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    app_name = Column(String(100), nullable=False)
    job_id = Column(String(100), nullable=True)
    backend_type = Column(String(50), nullable=False, default="duplicati")
    destination_path = Column(String(255), nullable=True)
    
    status = Column(SQLEnum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)
    progress_percentage = Column(Integer, default=0, nullable=False)
    
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    error_message = Column(String(500), nullable=True)
    execution_reference = Column(String(255), nullable=True)