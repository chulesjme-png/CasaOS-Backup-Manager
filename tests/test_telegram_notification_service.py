from unittest.mock import AsyncMock, patch
import pytest

from app.services.telegram_notification_service import (
    TelegramNotificationService,
)


@pytest.fixture
def telegram_service():
    return TelegramNotificationService(
        bot_token="TEST_BOT_TOKEN", chat_id="123456789"
    )


@pytest.mark.asyncio
async def test_notify_start_success(telegram_service):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        result = await telegram_service.notify_start("Sistema_Completo")

        assert result is True
        mock_post.assert_called_once()
        sent_text = mock_post.call_args[1]["json"]["text"]
        assert "[INICIO]" in sent_text
        assert "Sistema_Completo" in sent_text


@pytest.mark.asyncio
async def test_notify_cancel_success(telegram_service):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        result = await telegram_service.notify_cancel("Sistema_Completo")

        assert result is True
        mock_post.assert_called_once()
        sent_text = mock_post.call_args[1]["json"]["text"]
        assert "[CANCELADO]" in sent_text


@pytest.mark.asyncio
async def test_notify_error_success(telegram_service):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        result = await telegram_service.notify_error(
            "Sistema_Completo", "Sin espacio en disco"
        )

        assert result is True
        mock_post.assert_called_once()
        sent_text = mock_post.call_args[1]["json"]["text"]
        assert "[ERROR]" in sent_text
        assert "Sin espacio en disco" in sent_text


@pytest.mark.asyncio
async def test_notify_unconfigured_returns_false():
    unconfigured_service = TelegramNotificationService(
        bot_token=None, chat_id=None
    )
    result = await unconfigured_service.notify_cancel("Sistema_Completo")
    assert result is False