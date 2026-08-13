from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import config_manager
from app.services.notification_service import notification_service

router = APIRouter()

class NotificationSettings(BaseModel):
    webhook_enabled: bool
    webhook_url: str
    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str

@router.post("/notifications/settings")
async def save_notification_settings(settings: NotificationSettings):
    config = config_manager.config
    config.webhook_enabled = settings.webhook_enabled
    config.webhook_url = settings.webhook_url
    config.telegram_enabled = settings.telegram_enabled
    config.telegram_bot_token = settings.telegram_bot_token
    config.telegram_chat_id = settings.telegram_chat_id
    
    config_manager.save_config(config)
    return {"status": "success", "message": "Configuración de notificaciones guardada."}

@router.post("/notifications/test")
async def test_notification(settings: NotificationSettings):
    # Guardamos temporalmente para enviar la prueba
    await notification_service.send_notification(
        title="Prueba de Notificación",
        message="¡Las notificaciones de CasaOS Backup Manager están configuradas correctamente!",
        status="success"
    )
    return {"status": "success", "message": "Notificación de prueba enviada."}