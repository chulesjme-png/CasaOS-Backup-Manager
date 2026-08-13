from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
# Importa la instancia de tu servicio de notificaciones y gestor de configuración
from app.services.notification_service import notification_service

router = APIRouter()

# 1. Definir el modelo de datos que viene del HTML
class NotificationSettings(BaseModel):
    telegram_enabled: bool
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    webhook_enabled: bool
    webhook_url: Optional[str] = ""

# 2. Endpoint para GUARDAR la configuración
@router.post("/notifications/settings")
async function save_notification_settings(settings: NotificationSettings):
    try:
        # Guarda las variables en tu config.json o sistema de persistencia
        # Ejemplo: config_service.save_notifications(settings.dict())
        
        # También actualizas las credenciales en el servicio activo en memoria
        notification_service.update_config(settings.dict())
        
        return {"status": "ok", "message": "Configuración guardada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error guardando datos: {str(e)}")

# 3. Endpoint para PROBAR la notificación (Botón 'Probar Notificación')
@router.post("/notifications/test")
async function test_notification(settings: NotificationSettings):
    try:
        # Se intenta enviar un mensaje directo de prueba usando los datos introducidos
        success = await notification_service.send_test_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            webhook_url=settings.webhook_url,
            telegram_enabled=settings.telegram_enabled,
            webhook_enabled=settings.webhook_enabled
        )
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo enviar el mensaje. Revisa las credenciales.")
            
        return {"status": "ok", "message": "Notificación enviada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))