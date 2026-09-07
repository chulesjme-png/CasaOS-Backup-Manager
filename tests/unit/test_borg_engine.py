import asyncio
from unittest.mock import AsyncMock, patch
import pytest

from app.infrastructure.backup_engines.borg_engine import BorgEngine, BorgEngineError


@pytest.fixture
def borg_engine():
    return BorgEngine(borg_binary="borg")


@pytest.mark.asyncio
async def test_init_repository_success(borg_engine):
    mock_process = AsyncMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (b"", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        result = await borg_engine.init_repository("/path/to/repo", encryption="none")

        assert result == {"status": "success", "repo_path": "/path/to/repo"}
        mock_exec.assert_called_once_with(
            "borg",
            "init",
            "--encryption=none",
            "/path/to/repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )


@pytest.mark.asyncio
async def test_init_repository_failure(borg_engine):
    mock_process = AsyncMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = (b"", b"Repository already exists")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(BorgEngineError, match="Error al inicializar el repositorio Borg"):
            await borg_engine.init_repository("/invalid/path")


@pytest.mark.asyncio
async def test_create_backup_success_with_progress(borg_engine):
    mock_process = AsyncMock()
    mock_process.returncode = 0

    json_progress = b'{"type": "archive_progress", "original_size": 1024, "compressed_size": 512}\n'
    mock_process.stderr.readline = AsyncMock(side_effect=[json_progress, b""])
    mock_process.communicate.return_value = (
        b'{"archive": {"name": "backup-01"}, "stats": {"deduplicated_size": 256}}',
        b""
    )

    received_events = []

    def progress_handler(event):
        received_events.append(event)

    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        result = await borg_engine.create_backup(
            repo_path="/path/to/repo",
            archive_name="backup-01",
            sources=["/data/src"],
            compression="zstd,3",
            progress_callback=progress_handler
        )

        assert result["status"] == "completed"
        assert result["archive"] == "backup-01"
        assert result["summary"]["archive"]["name"] == "backup-01"
        assert len(received_events) == 1
        assert received_events[0]["type"] == "archive_progress"
        assert received_events[0]["original_size"] == 1024


@pytest.mark.asyncio
async def test_create_backup_failure(borg_engine):
    mock_process = AsyncMock()
    mock_process.returncode = 2
    mock_process.stderr.readline = AsyncMock(return_value=b"")
    mock_process.communicate.return_value = (b"", b"Command failed: Source path does not exist")

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        with pytest.raises(BorgEngineError, match="Error durante la creación del backup Borg"):
            await borg_engine.create_backup(
                repo_path="/path/to/repo",
                archive_name="failed-backup",
                sources=["/nonexistent/path"]
            )