from pydantic import BaseModel
from typing import Optional

class SystemConfig(BaseModel):
    duplicati_url: str
    duplicati_pass: Optional[str] = ""
    default_backup_path: str
    retention_days: int
    enable_notifications: bool = False
    webhook_url: Optional[str] = ""