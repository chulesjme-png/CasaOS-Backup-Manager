from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BackupOperationType(str, Enum):
    RUN_BACKUP = "RUN_BACKUP"
    RESTORE = "RESTORE"
    CANCEL = "CANCEL"


class BackupConfiguration(BaseModel):
    destination_url: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BackupExecutionReference(BaseModel):
    execution_id: str
    task_id: str
    backend: str


class BackupManifest(BaseModel):
    application: str
    sources: List[str] = Field(default_factory=list)
    excluded_sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    estimated_size: int = 0


class BackupExecutionApiRequest(BaseModel):
    application: str
    backend_name: str
    destination_url: str
    backup_id: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    excluded_sources: List[str] = Field(default_factory=list)


class BackupCancelApiRequest(BaseModel):
    application: str
    backend_name: str
    execution_reference: BackupExecutionReference


class BackupResult(BaseModel):
    success: bool
    backend: str
    application: str
    operation: BackupOperationType
    execution_reference: Optional[BackupExecutionReference] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackupResultResponse(BaseModel):
    success: bool
    backend: str
    application: str
    operation: str
    execution_reference: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)