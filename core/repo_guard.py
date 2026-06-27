import json
import os
from datetime import datetime

try:
    from core.tool_paths import ensure_tool_dir, tool_file
except ModuleNotFoundError:
    from stm32_git_release_tool.core.tool_paths import ensure_tool_dir, tool_file


GUARD_FILE = ".git_guard.json"


class RepoGuard:
    def __init__(self, project_path: str, git_service):
        self.project_path = project_path
        self.git = git_service
        self.guard_path = tool_file(project_path, GUARD_FILE)

    def exists(self) -> bool:
        return os.path.exists(self.guard_path)

    def load(self) -> dict:
        if not self.exists():
            return {}
        with open(self.guard_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def save(self, remote_url: str = "") -> dict:
        ensure_tool_dir(self.project_path)
        data = {
            "project_path": self.project_path,
            "git_existed": self.git.is_repository(),
            "head": self._safe_head(),
            "branch": self._safe_branch(),
            "remote_url": remote_url or self._safe_remote(),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(self.guard_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        return data

    def status(self) -> str:
        if self.exists() and not self.git.is_repository():
            return "missing_git"
        if self.git.is_repository() and not self.exists():
            return "unguarded"
        if self.git.is_repository() and self.exists():
            return "ok"
        return "no_repo"

    def _safe_head(self) -> str:
        if not self.git.is_repository():
            return ""
        result = self.git.run(["rev-parse", "HEAD"])
        return result.stdout.strip() if result.ok else ""

    def _safe_branch(self) -> str:
        if not self.git.is_repository():
            return ""
        return self.git.current_branch()

    def _safe_remote(self) -> str:
        if not self.git.is_repository():
            return ""
        result = self.git.run(["remote", "get-url", "origin"])
        return result.stdout.strip() if result.ok else ""
