import os
import json
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

CONFIG_DIR = Path("/DATA/AppData/casaos-backup-manager")
CONFIG_FILE = CONFIG_DIR / "config.json"

class AppConfig(BaseModel):
    version: str = "v0.5.0-alpha7"
    selected_target_disk: Optional[str] = None
    duplicati_url: str = "http://localhost:8200"
    retention_days: int = 30
    schedule_frequency: str = "daily"
    schedule_time: str = "03:00"

class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self) -> AppConfig:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return AppConfig(**data)
            except Exception as e:
                print(f"[ConfigManager] Error leyendo configuración: {e}. Usando valores por defecto.")
        
        default_config = AppConfig()
        self.save_config(default_config)
        return default_config

    def save_config(self, config: AppConfig) -> AppConfig:
        self.config = config
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(), f, indent=4)
        return self.config

    def update_key(self, key: str, value: any) -> AppConfig:
        data = self.config.model_dump()
        data[key] = value
        new_config = AppConfig(**data)
        return self.save_config(new_config)

config_manager = ConfigManager()