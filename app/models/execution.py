from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database.connection import Base

class ExecutionRecordModel(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, index=True)
    app_name = Column(String, nullable=False)
    backend_type = Column(String, default="duplicati")
    destination_path = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, RUNNING, SUCCESS, FAILED
    progress_percentage = Column(Integer, default=0)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScheduleRecordModel(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    app_name = Column(String, nullable=False)
    cron_expression = Column(String, nullable=False)  # Ej. "0 2 * * *"
    destination_path = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())