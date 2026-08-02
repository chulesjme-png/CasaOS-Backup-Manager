from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BackupOperationType(str, Enum):
    RUN_BACKUP = "run_backup"
    GET_STATUS = "get_status"
    CANCEL = "cancel"
    RESTORE = "restore"


class BackupExecutionReference(BaseModel):
    execution_id: Optional[str] = None
    task_id: Optional[str] = None
    backend: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackupConfiguration(BaseModel):
    destination_url: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)


class BackendConfiguration(BaseModel):
    backend_name: str
    enabled: bool = True
    configuration: Dict[str, Any] = Field(default_factory=dict)


class BackupSource(BaseModel):
    name: str
    path: str
    application: Optional[str] = None
    container: Optional[str] = None
    source_type: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackupManifest(BaseModel):
    application: str
    sources: List[str] = Field(default_factory=list)
    excluded_sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    estimated_size: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BackupExecutionRequest(BaseModel):
    manifest: BackupManifest
    backup_configuration: BackupConfiguration = Field(default_factory=BackupConfiguration)
    backend_name: str
    backend_configuration: Optional[BackendConfiguration] = None
    operation: BackupOperationType = BackupOperationType.RUN_BACKUP
    execution_reference: Optional[BackupExecutionReference] = None


class BackupResult(BaseModel):
    success: bool
    backend: str
    application: str
    operation: BackupOperationType = BackupOperationType.RUN_BACKUP
    execution_reference: Optional[BackupExecutionReference] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    bytes_processed: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
