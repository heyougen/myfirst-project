import fnmatch
import os
from typing import List


class ProjectScanner:
    FIRMWARE_PATTERNS = ["*.bin", "*.hex"]
    SKIP_DIRS = {".git", ".stm32_git_tool", "releases", "__pycache__"}

    def __init__(self, project_path: str):
        self.project_path = project_path

    def find_firmware_files(self) -> List[str]:
        files: List[str] = []
        for root, dirs, filenames in os.walk(self.project_path):
            dirs[:] = [dirname for dirname in dirs if dirname not in self.SKIP_DIRS]
            for filename in filenames:
                if any(fnmatch.fnmatch(filename.lower(), pattern) for pattern in self.FIRMWARE_PATTERNS):
                    files.append(os.path.join(root, filename))
        return files
