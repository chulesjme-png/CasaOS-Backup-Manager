import os
import json
import logging
from pathlib import Path
from typing import Optional, Union, Any
from pydantic import BaseModel

logger = logging.getLogger("casaos-backup")

CONFIG_DIR = Path("/DATA/AppData/casaos-backup-manager")
CONFIG_FILE = CONFIG_DIR / "config.json"

class AppConfig(BaseModel):
    version: str = "v0.5.0-alpha7"
    selected_target_disk: Optional[str] = None
    duplicati_url: str = "http://localhost:8200"
    retention_days: int = 30
    schedule_frequency: str = "daily"
    schedule_time: str = "03:00"
    
    # Parámetros de Notificaciones (Telegram y Webhook)
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    webhook_enabled: bool = False
    webhook_url: Optional[str] = ""

class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self) -> AppConfig:
        if CONFIG_FILE.exists():
            try:
                # Detección preventiva de archivos vacíos (0 bytes)
                if CONFIG_FILE.stat().st_size == 0:
                    logger.warning("[ConfigManager] El archivo config.json está vacío (0 bytes). Generando configuración por defecto...")
                    return self._create_default_config()

                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return AppConfig(**data)
            except Exception as e:
                logger.error(f"[ConfigManager] Error leyendo configuración ({e}). Regenerando archivo...")
                return self._create_default_config()
        
        return self._create_default_config()

    def _create_default_config(self) -> AppConfig:
        default_config = AppConfig()
        self.save_config(default_config)
        return default_config

    def save_config(self, config: Optional[Union[AppConfig, dict]] = None) -> AppConfig:
        """
        Persiste la configuración en disco mediante ESCRITURA ATÓMICA.
        Previene archivos de 0 bytes en reinicios o caídas de energía.
        """
        if config is None:
            config = self.config

        # 1. Normalización agnóstica a diccionario
        if hasattr(config, "model_dump"):
            data = config.model_dump()
        elif hasattr(config, "dict"):
            data = config.dict()
        elif isinstance(config, dict):
            data = config
        else:
            data = dict(config)

        # 2. Actualización de la instancia interna en memoria
        if isinstance(config, dict):
            self.config = AppConfig(**data)
        else:
            self.config = config

        # 3. Escritura Atómica en Disco (TMP -> Replace)
        temp_file = CONFIG_FILE.with_suffix(".json.tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            
            # Reemplazo atómico en nivel de Kernel/SISTEMA DE ARCHIVOS
            temp_file.replace(CONFIG_FILE)
            logger.info("[ConfigManager] Configuración persistida con éxito en disco.")
        except Exception as e:
            logger.error(f"[ConfigManager] Error crítico en la escritura de configuración: {e}")
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        return self.config

    def update_key(self, key: str, value: Any) -> AppConfig:
        """
        Actualiza un atributo con conversión dinámica de tipos.
        """
        if hasattr(self.config, "model_dump"):
            data = self.config.model_dump()
        else:
            data = self.config.dict()

        # Coerción de tipos para evitar inconsistencias HTTP/Payloads
        if key in data and isinstance(data[key], bool) and isinstance(value, str):
            value = value.lower() in ("true", "1", "t", "yes")
        elif key in data and isinstance(data[key], int) and isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                pass

        data[key] = value
        new_config = AppConfig(**data)
        return self.save_config(new_config)

config_manager = ConfigManager()