import json
import os
from typing import Any, Dict


DEFAULT_CONFIG: Dict[str, Any] = {
    "project_type": "STM32 Keil",
    "language": "zh_CN",
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

DEFAULT_APP_STATE: Dict[str, Any] = {
    "last_project_path": "",
    "recent_projects": [],
}


def user_config_dir() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "STM32GitReleaseTool")
    return os.path.join(os.path.expanduser("~"), ".stm32_git_release_tool")


def app_state_path() -> str:
    return os.path.join(user_config_dir(), "app_state.json")


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


class AppStateManager(ConfigManager):
    def __init__(self, state_path: str = None):
        super().__init__(state_path or app_state_path())

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return DEFAULT_APP_STATE.copy()
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError):
            return DEFAULT_APP_STATE.copy()
        state = DEFAULT_APP_STATE.copy()
        state.update(data)
        return state

    def save_last_project(self, project_path: str) -> None:
        if not project_path:
            return
        project_path = os.path.realpath(project_path)
        state = self.load()
        recent_projects = [
            path for path in state.get("recent_projects", [])
            if path and os.path.realpath(path) != project_path
        ]
        state["last_project_path"] = project_path
        state["recent_projects"] = [project_path] + recent_projects[:9]
        self.save(state)
