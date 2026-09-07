import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """
    Servicio encargado del envío de notificaciones de ciclo de vida del respaldo a Telegram.
    Soporta eventos de inicio, éxito, cancelación y error.
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = (
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            if self.bot_token
            else None
        )

    async def send_message(self, message: str) -> bool:
        """
        Envía un mensaje formateado en HTML a la API de Telegram.
        """
        if not self.bot_token or not self.chat_id:
            logger.warning(
                "TelegramNotificationService omitido: faltan bot_token o chat_id."
            )
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Error enviando notificación a Telegram: {e}")
            return False

    async def notify_start(self, job_name: str) -> bool:
        msg = f"🟢 <b>[INICIO]</b> Tarea de respaldo iniciada: <code>{job_name}</code>"
        return await self.send_message(msg)

    async def notify_success(self, job_name: str, details: str = "") -> bool:
        msg = (
            f"✅ <b>[ÉXITO]</b> Tarea de respaldo completada: <code>{job_name}</code>"
        )
        if details:
            msg += f"\n\n<b>Detalles:</b>\n{details}"
        return await self.send_message(msg)

    async def notify_cancel(self, job_name: str) -> bool:
        msg = (
            f"⚠️ <b>[CANCELADO]</b> Tarea de respaldo cancelada por el usuario o sistema: "
            f"<code>{job_name}</code>"
        )
        return await self.send_message(msg)

    async def notify_error(self, job_name: str, error_msg: str) -> bool:
        msg = (
            f"🚨 <b>[ERROR]</b> Fallo crítico en tarea de respaldo: <code>{job_name}</code>\n"
            f"<b>Detalle:</b> {error_msg}"
        )
        return await self.send_message(msg)