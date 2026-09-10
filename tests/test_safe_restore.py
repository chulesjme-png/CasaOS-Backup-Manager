import pytest
from pathlib import Path
from app.services.staging_manager import StagingManager
from app.services.restore_service import RestoreService

def test_staging_isolation_and_atomic_swap(tmp_path):
    app_data = tmp_path / "AppData"
    app_data.mkdir()
    
    original_app = app_data / "netdata"
    original_app.mkdir()
    (original_app / "config.json").write_text('{"version": 1}')

    staging_mgr = StagingManager(base_app_data_path=str(app_data))
    task_id = "task_test_001"
    
    staging_path = staging_mgr.create_staging_area(task_id)
    (staging_path / "config.json").write_text('{"version": 2}')

    staging_mgr.atomic_swap(task_id, "netdata")

    assert (original_app / "config.json").read_text() == '{"version": 2}'
    assert not (app_data / ".restore_staging").exists()

def test_rollback_on_swap_failure(tmp_path, mocker):
    app_data = tmp_path / "AppData"
    app_data.mkdir()
    
    original_app = app_data / "netdata"
    original_app.mkdir()
    (original_app / "config.json").write_text('{"version": 1}')

    staging_mgr = StagingManager(base_app_data_path=str(app_data))
    task_id = "task_test_fail"
    staging_path = staging_mgr.create_staging_area(task_id)

    mocker.patch("shutil.move", side_effect=[True, RuntimeError("Simulación de fallo de disco")])

    with pytest.raises(RuntimeError) as excinfo:
        staging_mgr.atomic_swap(task_id, "netdata")

    assert "Rollback completado con éxito" in str(excinfo.value)
    assert (original_app / "config.json").read_text() == '{"version": 1}'