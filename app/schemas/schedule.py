from pydantic import BaseModel
from typing import Optional, List

class ScheduleCreate(BaseModel):
    frequency: str  # "daily", "weekly", "disabled"
    time: str       # "03:00"
    days: Optional[List[str]] = []  # ["mon", "wed", "fri"]
    backup_type: str # "full" o "apps"
    enabled: bool = True

class ScheduleResponse(ScheduleCreate):
    id: int

    class Config:
        from_attributes = True