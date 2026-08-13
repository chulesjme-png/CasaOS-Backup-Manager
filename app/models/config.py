from pydantic import BaseModel
from typing import Optional

class AppConfig(BaseModel):
    version: str = "v0.5.0-alpha7"
    selected_target_disk: str = "/media/pichules/08604ab9-10b8-a6fc-a19f3adfc6fa"
    
    # Configuración de Notificaciones
    webhook_enabled: bool = False
    webhook_url: Optional[str] = ""
    
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""