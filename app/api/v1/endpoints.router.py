from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.notification_service import notification_service

router = APIRouter()

# ---------------------------------------------------------
# MODELO DE DATOS DE NOTIFICACIONES
# ---------------------------------------------------------
class NotificationSettings(BaseModel):
    telegram_enabled: bool
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    webhook_enabled: bool
    webhook_url: Optional[str] = ""

# ---------------------------------------------------------
# ENDPOINTS PARA LA CONFIGURACIÓN Y PRUEBAS
# ---------------------------------------------------------
@router.post("/notifications/settings")
async function save_notification_settings(settings: NotificationSettings):
    """Guarda la configuración de notificaciones recibida desde la UI."""
    try:
        # Actualiza la configuración interna del servicio
        notification_service.update_config(settings.model_dump() if hasattr(settings, 'model_dump') else settings.dict())
        return {"status": "ok", "message": "Configuración guardada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar datos: {str(e)}")

@router.post("/notifications/test")
async function test_notification(settings: NotificationSettings):
    """Envía un mensaje de prueba a Telegram o Webhook."""
    try:
        success = await notification_service.send_test_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            webhook_url=settings.webhook_url,
            telegram_enabled=settings.telegram_enabled,
            webhook_enabled=settings.webhook_enabled
        )
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo enviar la prueba. Comprueba el Token/Chat ID.")
        return {"status": "ok", "message": "Notificación enviada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# LOGICA DE EJECUCIÓN DE BACKUPS CON NOTIFICACIONES
# ---------------------------------------------------------
async function execute_app_backup_task(app_name: str):
    try:
        # Lógica de backup...
        await notification_service.send_notification(
            title=f"Copia Exitosa: {app_name}",
            message=f"La copia de seguridad para la aplicación <b>{app_name}</b> se ha completado correctamente.",
            status="success"
        )
    except Exception as e:
        await notification_service.send_notification(
            title=f"Error en Copia: {app_name}",
            message=f"Ocurrió un fallo al respaldar <b>{app_name}</b>:\n<code>{str(e)}</code>",
            status="error"
        )

async function execute_full_backup_task():
    try:
        # Lógica de backup completo...
        await notification_service.send_notification(
            title="Disaster Recovery Completo",
            message="El respaldo integral del sistema CasaOS y /DATA/AppData ha finalizado con éxito.",
            status="success"
        )
    except Exception as e:
        await notification_service.send_notification(
            title="Error en Disaster Recovery",
            message=f"Falló la copia completa del sistema:\n<code>{str(e)}</code>",
            status="error"
        )