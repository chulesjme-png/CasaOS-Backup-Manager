import httpx
import logging
from app.core.config import config_manager

logger = logging.getLogger("casaos_backup_manager")

class NotificationService:
    def __init__(self):
        pass

    async def send_notification(self, title: str, message: str, status: str = "info"):
        """Envía notificaciones según los canales activos en la configuración."""
        config = config_manager.config

        # Elegir emoji según estado
        emoji = "✅" if status == "success" else "❌" if status == "error" else "ℹ️"
        full_title = f"{emoji} {title}"

        # 1. Enviar por Webhook (Discord / Slack / N8n / Apprise)
        if config.webhook_enabled and config.webhook_url:
            await self._send_webhook(config.webhook_url, full_title, message)

        # 2. Enviar por Telegram
        if config.telegram_enabled and config.telegram_bot_token and config.telegram_chat_id:
            await self._send_telegram(
                config.telegram_bot_token, 
                config.telegram_chat_id, 
                f"<b>{full_title}</b>\n\n{message}"
            )

    async def _send_webhook(self, url: str, title: str, message: str):
        try:
            payload = {
                "username": "CasaOS Backup Manager",
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 3066993 if "✅" in title else 15158332
                }] if "discord" in url else None,
                "text": f"*{title}*\n{message}"
            }
            # Filtrar payload de acuerdo a la plataforma
            body = {k: v for k, v in payload.items() if v is not None}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                logger.info("🟢 Webhook enviado con éxito.")
        except Exception as e:
            logger.error(f"🔴 Error al enviar Webhook: {e}")

    async def _send_telegram(self, token: str, chat_id: str, text: str):
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info("🟢 Mensaje de Telegram enviado con éxito.")
        except Exception as e:
            logger.error(f"🔴 Error al enviar mensaje a Telegram: {e}")

notification_service = NotificationService()