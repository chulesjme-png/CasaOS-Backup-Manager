import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.services.telegram_notification_service import TelegramNotificationService
from app.infrastructure.process_manager import ProcessManager
from app.infrastructure.backup_engines.borg_engine import BorgEngine, BorgEngineError


@pytest.fixture
def telegram_service():
    return TelegramNotificationService(bot_token="TEST_TOKEN", chat_id="123456")


@pytest.fixture
def process_manager():
    return ProcessManager()


@pytest.fixture
def borg_engine():
    return BorgEngine(borg_binary="borg")


@pytest.mark.asyncio
async def test_full_backup_flow_success(process_manager, borg_engine, telegram_service, tmp_path):
    temp_dir = tmp_path / ".tmp_incremental_Sistema_Completo"
    temp_dir.mkdir()

    job_name = "Sistema_Completo"
    repo_path = str(tmp_path / "repo")

    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.stderr.readline = AsyncMock(return_value=b"")
    mock_process.communicate.return_value = (
        b'{"archive": {"name": "backup-01"}, "stats": {"deduplicated_size": 100}}',
        b""
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_telegram, \
         patch("asyncio.create_subprocess_exec", return_value=mock_process):
        
        mock_telegram.return_value.status_code = 200
        mock_telegram.return_value.raise_for_status = lambda: None

        # 1. Notificación de Inicio
        await telegram_service.notify_start(job_name)

        # 2. Ejecución protegida con ProcessManager
        async def run_backup():
            return await borg_engine.create_backup(
                repo_path=repo_path,
                archive_name="backup-01",
                sources=[str(tmp_path)]
            )

        result = await process_manager.run_with_cleanup(
            run_backup,
            cleanup_paths=[str(temp_dir)]
        )

        # 3. Notificación de Éxito
        await telegram_service.notify_success(job_name, details="Respaldo completado en Borg")

        # Verificaciones
        assert result["status"] == "completed"
        assert not temp_dir.exists()
        assert mock_telegram.call_count == 2
        assert "[INICIO]" in mock_telegram.call_args_list[0][1]["json"]["text"]
        assert "[ÉXITO]" in mock_telegram.call_args_list[1][1]["json"]["text"]


@pytest.mark.asyncio
async def test_backup_flow_failure_cleans_dir_and_notifies_telegram(
    process_manager, borg_engine, telegram_service, tmp_path
):
    temp_dir = tmp_path / ".tmp_incremental_Sistema_Completo"
    temp_dir.mkdir()
    assert temp_dir.exists()

    job_name = "Sistema_Completo"

    mock_process = AsyncMock()
    mock_process.returncode = 2
    mock_process.stderr.readline = AsyncMock(return_value=b"")
    mock_process.communicate.return_value = (b"", b"Disk full error")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_telegram, \
         patch("asyncio.create_subprocess_exec", return_value=mock_process):

        mock_telegram.return_value.status_code = 200
        mock_telegram.return_value.raise_for_status = lambda: None

        async def run_failing_backup():
            return await borg_engine.create_backup(
                repo_path="/path/to/repo",
                archive_name="failed-backup",
                sources=[str(tmp_path)]
            )

        async def on_error_callback(exc):
            await telegram_service.notify_error(job_name, str(exc))

        with pytest.raises(BorgEngineError):
            await process_manager.run_with_cleanup(
                run_failing_backup,
                cleanup_paths=[str(temp_dir)],
                on_error=on_error_callback
            )

        # Verificaciones de limpieza y alerta
        assert not temp_dir.exists()
        mock_telegram.assert_called_once()
        sent_text = mock_telegram.call_args[1]["json"]["text"]
        assert "[ERROR]" in sent_text
        assert "Error durante la creación del backup Borg" in sent_text


@pytest.mark.asyncio
async def test_backup_flow_cancellation_cleans_dir_and_notifies_telegram(
    process_manager, telegram_service, tmp_path
):
    temp_dir = tmp_path / ".tmp_incremental_Sistema_Completo"
    temp_dir.mkdir()
    assert temp_dir.exists()

    job_name = "Sistema_Completo"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_telegram:
        mock_telegram.return_value.status_code = 200
        mock_telegram.return_value.raise_for_status = lambda: None

        async def run_cancelled_backup():
            raise asyncio.CancelledError()

        async def on_cancel_callback():
            await telegram_service.notify_cancel(job_name)

        with pytest.raises(asyncio.CancelledError):
            await process_manager.run_with_cleanup(
                run_cancelled_backup,
                cleanup_paths=[str(temp_dir)],
                on_cancel=on_cancel_callback
            )

        # Verificaciones tras interrupción manual / SIGTERM
        assert not temp_dir.exists()
        mock_telegram.assert_called_once()
        sent_text = mock_telegram.call_args[1]["json"]["text"]
        assert "[CANCELADO]" in sent_text