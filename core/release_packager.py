import fnmatch
import os
import shutil
import tempfile
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional


LogCallback = Optional[Callable[[str], None]]


class ReleasePackager:
    def __init__(self, project_path: str, config: Dict, log: LogCallback = None):
        self.project_path = project_path
        self.config = config
        self.log = log

    def _log(self, message: str) -> None:
        if self.log:
            self.log(message)

    def _is_excluded(self, path: str) -> bool:
        rel = os.path.relpath(path, self.project_path)
        parts = rel.split(os.sep)
        if any(part in {".git", ".stm32_git_tool"} for part in parts):
            return True
        if any(part in self.config.get("exclude_dirs", []) for part in parts):
            return True
        name = os.path.basename(path)
        return any(fnmatch.fnmatch(name, pattern) for pattern in self.config.get("exclude_patterns", []))

    def _copy_tree_filtered(self, src: str, dst: str) -> None:
        for root, dirs, files in os.walk(src):
            dirs[:] = [dirname for dirname in dirs if not self._is_excluded(os.path.join(root, dirname))]
            rel_root = os.path.relpath(root, src)
            out_root = dst if rel_root == "." else os.path.join(dst, rel_root)
            os.makedirs(out_root, exist_ok=True)
            for filename in files:
                source_file = os.path.join(root, filename)
                if self._is_excluded(source_file):
                    continue
                shutil.copy2(source_file, os.path.join(out_root, filename))

    def _copy_firmware(self, firmware_files: Iterable[str], release_root: str) -> List[str]:
        out_dir = os.path.join(release_root, "firmware")
        os.makedirs(out_dir, exist_ok=True)
        copied: List[str] = []
        for firmware in firmware_files:
            if os.path.isfile(firmware):
                target = os.path.join(out_dir, os.path.basename(firmware))
                shutil.copy2(firmware, target)
                copied.append(target)
                self._log(f"[固件] {firmware}")
        if not copied:
            self._log("[提示] 未找到 .bin 或 .hex 固件文件，发布包仍会生成。")
        return copied

    def create_release(self, version: str, description: str, firmware_files: Iterable[str]) -> str:
        release_dir = self.config.get("release_dir", ".stm32_git_tool/releases")
        if not os.path.isabs(release_dir):
            release_dir = os.path.join(self.project_path, release_dir)
        os.makedirs(release_dir, exist_ok=True)

        archive_base = os.path.join(release_dir, f"Release_{version}")
        with tempfile.TemporaryDirectory() as temp_dir:
            release_root = os.path.join(temp_dir, f"Release_{version}")
            source_root = os.path.join(release_root, "src")
            os.makedirs(source_root, exist_ok=True)

            include_dirs = self.config.get("include_source_dirs", [])
            copied_any = False
            for dirname in include_dirs:
                source_dir = os.path.join(self.project_path, dirname)
                if os.path.isdir(source_dir):
                    self._copy_tree_filtered(source_dir, os.path.join(source_root, dirname))
                    copied_any = True
            if not copied_any:
                self._log("[提示] 未匹配到配置的源码目录，改为打包工程根目录并套用排除规则。")
                self._copy_tree_filtered(self.project_path, source_root)

            self._copy_firmware(firmware_files, release_root)
            self._write_release_files(release_root, version, description)
            archive_path = shutil.make_archive(archive_base, "zip", temp_dir, f"Release_{version}")

        self._log(f"[发布包] {archive_path}")
        return archive_path

    def _write_release_files(self, release_root: str, version: str, description: str) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        version_text = f"version={version}\nbuild_time={now}\n"
        note_text = f"Release: {version}\nTime: {now}\n\nDescription:\n{description.strip()}\n"
        readme_text = "STM32 project release package.\n\n包含 firmware、src、ReleaseNote.txt 和 version.txt。\n"
        with open(os.path.join(release_root, "version.txt"), "w", encoding="utf-8") as file:
            file.write(version_text)
        with open(os.path.join(release_root, "ReleaseNote.txt"), "w", encoding="utf-8") as file:
            file.write(note_text)
        with open(os.path.join(release_root, "README.txt"), "w", encoding="utf-8") as file:
            file.write(readme_text)
