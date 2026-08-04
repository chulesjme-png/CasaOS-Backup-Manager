from pydantic import BaseModel, Field
from typing import List, Optional

class AppProfile(BaseModel):
    app_id: str
    app_name: str
    container_names: List[str]
    paths_to_include: List[str]
    paths_to_exclude: List[str] = Field(default_factory=lambda: [
        "*.tmp",
        "*.log",
        "cache/*",
        "Cache/*",
        "*.sock"
    ])
    pre_backup_hook: Optional[str] = None
    post_backup_hook: Optional[str] = None
    is_active: bool = True