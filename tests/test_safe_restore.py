import pytest
from pathlib import Path
from app.services.staging_manager import StagingManager

def test_staging_area_creation(tmp_path):
    staging_mgr = StagingManager(base_app_data_path=str(tmp_path))
    task_id = "test_task_001"
    
    staging_path = staging_mgr.create_staging_area(task_id)
    assert staging_path.exists()
    assert staging_path == tmp_path / ".restore_staging" / task_id

def test_disk_space_check(tmp_path):
    staging_mgr = StagingManager(base_app_data_path=str(tmp_path))
    assert staging_mgr.verify_disk_space(required_bytes=500) is True

def test_atomic_swap_and_rollback(tmp_path):
    staging_mgr = StagingManager(base_app_data_path=str(tmp_path))
    task_id = "test_swap_task"
    app_name = "netdata"

    app_dir = tmp_path / app_name
    app_dir.mkdir()
    (app_dir / "config.env").write_text("OLD_DATA=1")

    staging_dir = staging_mgr.create_staging_area(task_id)
    (staging_dir / "config.env").write_text("NEW_DATA=1")

    success = staging_mgr.atomic_swap(task_id, app_name)
    assert success is True
    assert (app_dir / "config.env").read_text() == "NEW_DATA=1"