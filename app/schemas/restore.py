from pydantic import BaseModel
from typing import Optional

class RestoreRequest(BaseModel):
    snapshot_id: str
    target_app: Optional[str] = None
    overwrite: bool = True