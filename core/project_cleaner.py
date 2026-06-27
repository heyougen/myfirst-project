import fnmatch
import os
import shutil
from typing import Callable, List, Optional


LogCallback = Optional[Callable[[str], None]]


class ProjectCleaner:
    BUILD_DIRS = ["Debug", "Objects", "Listings"]
    BUILD_PATTERNS = ["*.map", "*.axf", "*.o", "*.d"]
    SKIP_DIRS = {".git", ".stm32_git_tool", "releases", "diff_reports", "diagnostics", "logs"}

    def __init__(self, project_path: str, log: LogCallback = None):
        self.project_path = project_path
        self.log = log

    def _log(self, message: str) -> None:
        if self.log:
            self.log(message)

    def scan(self) -> List[str]:
        targets: List[str] = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [dirname for dirname in dirs if dirname not in self.SKIP_DIRS]
            for dirname in list(dirs):
                if dirname in self.BUILD_DIRS:
                    targets.append(os.path.join(root, dirname))
                    dirs.remove(dirname)
            for filename in files:
                if any(fnmatch.fnmatch(filename, pattern) for pattern in self.BUILD_PATTERNS):
                    targets.append(os.path.join(root, filename))
        return targets

    def clean(self) -> List[str]:
        removed: List[str] = []
        for target in self.scan():
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                elif os.path.isfile(target):
                    os.remove(target)
                removed.append(target)
                self._log(f"[清理] {target}")
            except PermissionError as exc:
                self._log(f"[权限错误] {target}: {exc}")
            except OSError as exc:
                self._log(f"[删除失败] {target}: {exc}")
        self._log(f"[完成] 清理 {len(removed)} 项")
        return removed
