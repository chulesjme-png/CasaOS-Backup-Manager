from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionCreate(BaseModel):
    app_name: str
    job_id: Optional[str] = None
    backend_type: str = "duplicati"
    destination_path: Optional[str] = None


class ExecutionUpdate(BaseModel):
    status: Optional[ExecutionStatus] = None
    progress_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_reference: Optional[str] = None


class ExecutionResponse(BaseModel):
    id: str
    app_name: str
    job_id: Optional[str]
    backend_type: str
    destination_path: Optional[str]
    status: ExecutionStatus
    progress_percentage: int
    start_time: datetime
    end_time: Optional[datetime]
    error_message: Optional[str]
    execution_reference: Optional[str]

    class Config:
        from_attributes = True