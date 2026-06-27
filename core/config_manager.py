import json
import os
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "project_type": "STM32 Keil",
    "protection_enabled": False,
    "password_hash": "",
    "password_salt": "",
    "firmware_dir": "",
    "release_dir": ".stm32_git_tool/releases",
    "include_source_dirs": ["Core", "Drivers", "Inc", "Src", "User", "UserAPP", "MDK-ARM"],
    "exclude_dirs": [".git", ".stm32_git_tool", "Debug", "Objects", "Listings", "build", "__pycache__"],
    "exclude_patterns": ["*.map", "*.axf", "*.o", "*.d", "*.lst", "*.dep"],
    "firmware_patterns": ["*.bin", "*.hex"],
    "remote": "",
    "recent_projects": [],
}


class ConfigManager:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return DEFAULT_CONFIG.copy()
        with open(self.config_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        config = DEFAULT_CONFIG.copy()
        config.update(data)
        return config

    def save(self, config: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent=2)
