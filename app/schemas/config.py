from pydantic import BaseModel
from typing import Optional

class SystemConfig(BaseModel):
    duplicati_url: str = "http://localhost:8200"
    duplicati_pass: Optional[str] = ""
    default_backup_path: str = "/mnt/backups"
    retention_days: int = 30
    enable_notifications: bool = False
    webhook_url: Optional[str] = ""