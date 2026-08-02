from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BackupManifest(BaseModel):
    application: str
    sources: List[str] = Field(default_factory=list)
    excluded_sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    estimated_size: int = 0


class BackupConfiguration(BaseModel):
    destination_url: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class BackupExecutionReference(BaseModel):
    execution_id: str
    task_id: Optional[str] = None
    backend: str


class BackupExecutionApiRequest(BaseModel):
    application: str
    sources: List[str] = Field(default_factory=list)
    excluded_sources: List[str] = Field(default_factory=list)
    backend_name: str
    destination_url: str
    backup_id: Optional[str] = None
    backend_url: str = "http://localhost:8200"
    backend_password: str = ""


class BackupResult(BaseModel):
    success: bool
    backend: str
    application: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    bytes_processed: int = 0
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    execution_reference: Optional[BackupExecutionReference] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)