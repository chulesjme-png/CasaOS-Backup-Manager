import logging
import httpx
from typing import Optional, Dict, Any
from app.core.config import config_manager

logger = logging.getLogger("casaos-backup")

class NotificationService:
    def __init__(self):
        # Cargar configuración inicial desde config_manager si existe
        self.telegram_enabled = getattr(config_manager.config, "telegram_enabled", False)
        self.telegram_bot_token = getattr(config_manager.config, "telegram_bot_token", "")
        self.telegram_chat_id = getattr(config_manager.config, "telegram_chat_id", "")
        self.webhook_enabled = getattr(config_manager.config, "webhook_enabled", False)
        self.webhook_url = getattr(config_manager.config, "webhook_url", "")

    def update_config(self, config_data: Dict[str, Any]):
        """Actualiza la configuración activa del servicio en memoria."""
        self.telegram_enabled = config_data.get("telegram_enabled", self.telegram_enabled)
        self.telegram_bot_token = config_data.get("telegram_bot_token", self.telegram_bot_token)
        self.telegram_chat_id = config_data.get("telegram_chat_id", self.telegram_chat_id)
        self.webhook_enabled = config_data.get("webhook_enabled", self.webhook_enabled)
        self.webhook_url = config_data.get("webhook_url", self.webhook_url)
        logger.info("[NotificationService] Configuración de notificaciones actualizada en memoria.")

    async def send_telegram(self, message: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
        bot_token = token or self.telegram_bot_token
        c_id = chat_id or self.telegram_chat_id

        if not bot_token or not c_id:
            logger.warning("Faltan credenciales de Telegram para enviar la notificación.")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": c_id,
            "text": message,
            "parse_mode": "HTML"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    return True
                else:
                    logger.error(f"Error enviando Telegram ({response.status_code}): {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error de red enviando mensaje por Telegram: {e}")
            return False

    async def send_webhook(self, title: str, message: str, status: str = "info", url: Optional[str] = None) -> bool:
        target_url = url or self.webhook_url
        if not target_url:
            logger.warning("Falta la URL de Webhook para enviar la notificación.")
            return False

        payload = {
            "title": title,
            "message": message,
            "status": status
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(target_url, json=payload)
                return response.status_code in [200, 201, 202, 204]
        except Exception as e:
            logger.error(f"Error de red enviando Webhook: {e}")
            return False

    async def send_test_message(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
        telegram_enabled: bool = False,
        webhook_enabled: bool = False
    ) -> bool:
        success = True
        if telegram_enabled and token and chat_id:
            msg = "🤖 <b>CasaOS Backup Manager</b>\n\n¡Mensaje de prueba enviado con éxito!"
            res = await self.send_telegram(msg, token=token, chat_id=chat_id)
            if not res:
                success = False

        if webhook_enabled and webhook_url:
            res = await self.send_webhook(
                title="Prueba de Notificación",
                message="Mensaje de prueba enviado con éxito desde CasaOS Backup Manager.",
                status="info",
                url=webhook_url
            )
            if not res:
                success = False

        return success

    async def send_notification(self, title: str, message: str, status: str = "info"):
        """Envía notificación a todos los canales habilitados."""
        if self.telegram_enabled:
            formatted_msg = f"<b>{title}</b>\n\n{message}"
            await self.send_telegram(formatted_msg)

        if self.webhook_enabled:
            await self.send_webhook(title, message, status)

# Instancia singleton para uso en toda la app
notification_service = NotificationService()