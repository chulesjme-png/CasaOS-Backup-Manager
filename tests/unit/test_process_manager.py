import asyncio
from unittest.mock import AsyncMock
import pytest

from app.infrastructure.process_manager import ProcessManager


@pytest.fixture
def process_manager():
    return ProcessManager()


@pytest.mark.asyncio
async def test_run_with_cleanup_success_deletes_temp_dir(process_manager, tmp_path):
    temp_dir = tmp_path / ".tmp_incremental_test"
    temp_dir.mkdir()
    assert temp_dir.exists()

    async def successful_task():
        return "ok"

    result = await process_manager.run_with_cleanup(
        successful_task,
        cleanup_paths=[str(temp_dir)]
    )

    assert result == "ok"
    assert not temp_dir.exists()


@pytest.mark.asyncio
async def test_run_with_cleanup_on_exception_triggers_callback_and_cleans(process_manager, tmp_path):
    temp_dir = tmp_path / ".tmp_incremental_test"
    temp_dir.mkdir()
    on_error_mock = AsyncMock()

    async def failing_task():
        raise ValueError("Error durante el respaldo")

    with pytest.raises(ValueError, match="Error durante el respaldo"):
        await process_manager.run_with_cleanup(
            failing_task,
            cleanup_paths=[str(temp_dir)],
            on_error=on_error_mock
        )

    assert not temp_dir.exists()
    on_error_mock.assert_called_once()


@pytest.mark.asyncio
async def test_run_with_cleanup_on_cancellation_triggers_callback_and_cleans(process_manager, tmp_path):
    temp_dir = tmp_path / ".tmp_incremental_test"
    temp_dir.mkdir()
    on_cancel_mock = AsyncMock()

    async def cancelled_task():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await process_manager.run_with_cleanup(
            cancelled_task,
            cleanup_paths=[str(temp_dir)],
            on_cancel=on_cancel_mock
        )

    assert not temp_dir.exists()
    on_cancel_mock.assert_called_once()