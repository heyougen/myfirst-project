import difflib
import fnmatch
import hashlib
import os
from typing import Any, Dict, List, Optional, Tuple

try:
    from core.operation_control import CancellationToken
except ModuleNotFoundError:
    from stm32_git_release_tool.core.operation_control import CancellationToken


TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp",
    ".s", ".asm", ".inc", ".ld", ".icf", ".sct",
    ".py", ".json", ".xml", ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".txt", ".md", ".csv", ".bat", ".cmd", ".ps1", ".sh",
    ".uvprojx", ".uvoptx", ".uvmpw", ".ioc", ".mk", ".cmake",
}

SOURCE_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx", ".s", ".asm",
    ".py", ".js", ".ts", ".java", ".go", ".rs",
}
HEADER_EXTENSIONS = {".h", ".hh", ".hpp", ".inc"}
PROJECT_EXTENSIONS = {
    ".uvprojx", ".uvoptx", ".uvmpw", ".ioc", ".ld", ".icf", ".sct",
    ".mk", ".cmake", ".ini", ".cfg", ".toml",
}
DOCUMENT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".xml", ".yml", ".yaml"}
BINARY_EXTENSIONS = {
    ".bin", ".hex", ".axf", ".elf", ".out", ".map", ".o", ".obj",
    ".lib", ".a", ".dll", ".exe", ".zip", ".7z",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".stm32_git_tool",
    "__pycache__",
    "debug",
    "objects",
    "listings",
    "build",
}


class DirectoryComparer:
    def __init__(self, base_dir: str, target_dir: str, config: Optional[Dict[str, Any]] = None):
        self.base_dir = os.path.realpath(base_dir)
        self.target_dir = os.path.realpath(target_dir)
        self.config = config or {}
        configured_dirs = self.config.get("exclude_dirs", [])
        self.exclude_dirs = {name.casefold() for name in DEFAULT_EXCLUDE_DIRS}
        self.exclude_dirs.update(
            str(name).strip().replace("\\", "/").strip("/").casefold()
            for name in configured_dirs
            if str(name).strip()
        )
        self.exclude_patterns = [
            str(pattern).strip()
            for pattern in self.config.get("exclude_patterns", [])
            if str(pattern).strip()
        ]
        self._last_progress_percent = None

    def compare(self, cancel_token: Optional[CancellationToken] = None, progress_callback=None) -> Dict[str, Any]:
        self._validate()
        self._last_progress_percent = None
        self._progress(progress_callback, 2, "正在扫描旧工程")
        base_files, base_errors = self._scan(self.base_dir, cancel_token, progress_callback)
        self._progress(progress_callback, 6, "正在扫描新工程")
        target_files, target_errors = self._scan(self.target_dir, cancel_token, progress_callback)
        base_paths = set(base_files)
        target_paths = set(target_files)

        added = sorted(target_paths - base_paths, key=str.casefold)
        removed = sorted(base_paths - target_paths, key=str.casefold)
        modified = []
        same_count = 0

        common_paths = sorted(base_paths & target_paths, key=str.casefold)
        for index, relative_path in enumerate(common_paths, 1):
            self._check(cancel_token)
            self._progress(
                progress_callback,
                10 + int(45 * index / max(len(common_paths), 1)),
                f"正在比较文件（{index}/{len(common_paths)}）",
            )
            base_path = base_files[relative_path]
            target_path = target_files[relative_path]
            base_size = os.path.getsize(base_path)
            target_size = os.path.getsize(target_path)
            base_hash = self._sha256(base_path, cancel_token)
            target_hash = self._sha256(target_path, cancel_token)
            if base_size == target_size and base_hash == target_hash:
                same_count += 1
                continue
            modified.append({
                "path": relative_path,
                "base_size": base_size,
                "target_size": target_size,
                "base_hash": base_hash,
                "target_hash": target_hash,
                "binary": not self._is_text_path(relative_path),
            })

        added, removed, renamed = self._detect_renames(
            added,
            removed,
            base_files,
            target_files,
            cancel_token,
            progress_callback,
        )
        return {
            "base_dir": self.base_dir,
            "target_dir": self.target_dir,
            "base_count": len(base_files),
            "target_count": len(target_files),
            "added": added,
            "removed": removed,
            "modified": modified,
            "renamed": renamed,
            "same_count": same_count,
            "errors": base_errors + target_errors,
        }

    def prepare_diffs(
        self,
        result: Dict[str, Any],
        cancel_token: Optional[CancellationToken] = None,
        progress_callback=None,
    ) -> None:
        changes = []
        for path in result["added"]:
            changes.append(("added", path, None, os.path.join(self.target_dir, path)))
        for path in result["removed"]:
            changes.append(("removed", path, os.path.join(self.base_dir, path), None))
        for item in result["modified"]:
            path = item["path"]
            changes.append(("modified", path, os.path.join(self.base_dir, path), os.path.join(self.target_dir, path)))
        for item in result.get("renamed", []):
            changes.append((
                "renamed",
                item["to"],
                os.path.join(self.base_dir, item["from"]),
                os.path.join(self.target_dir, item["to"]),
            ))

        cache = {}
        for index, (status, path, base_path, target_path) in enumerate(changes, 1):
            self._check(cancel_token)
            self._progress(
                progress_callback,
                70 + int(30 * index / max(len(changes), 1)),
                f"正在生成差异（{index}/{len(changes)}）",
            )
            if status == "renamed":
                rename = next(item for item in result["renamed"] if item["to"] == path)
                cache[(status, path)] = self._file_diff(
                    path,
                    "RENAMED",
                    base_path,
                    target_path,
                    base_relative_path=rename["from"],
                    cancel_token=cancel_token,
                )
            else:
                cache[(status, path)] = self._file_diff(
                    path,
                    status.upper(),
                    base_path,
                    target_path,
                    cancel_token=cancel_token,
                )
        result["_diff_cache"] = cache
        self._progress(progress_callback, 100, "工程对比完成")

    def build_diff(self, result: Dict[str, Any], max_chars: Optional[int] = None) -> str:
        sections = []
        modified_by_path = {item["path"]: item for item in result["modified"]}
        changed_paths = sorted(
            set(result["added"]) | set(result["removed"]) | set(modified_by_path),
            key=str.casefold,
        )

        for relative_path in changed_paths:
            if relative_path in result["added"]:
                status = "ADDED"
                base_path = None
                target_path = os.path.join(self.target_dir, relative_path)
            elif relative_path in result["removed"]:
                status = "REMOVED"
                base_path = os.path.join(self.base_dir, relative_path)
                target_path = None
            else:
                status = "MODIFIED"
                base_path = os.path.join(self.base_dir, relative_path)
                target_path = os.path.join(self.target_dir, relative_path)

            cache_key = (status.casefold(), relative_path)
            cached = result.get("_diff_cache", {}).get(cache_key)
            sections.append(cached or self._file_diff(relative_path, status, base_path, target_path))

        for rename in result.get("renamed", []):
            cache_key = ("renamed", rename["to"])
            cached = result.get("_diff_cache", {}).get(cache_key)
            sections.append(cached or self._file_diff(
                rename["to"],
                "RENAMED",
                os.path.join(self.base_dir, rename["from"]),
                os.path.join(self.target_dir, rename["to"]),
                base_relative_path=rename["from"],
            ))

        text = "\n".join(section for section in sections if section)
        if result["errors"]:
            error_text = "\n".join(f"  {item}" for item in result["errors"])
            text += f"\n\nDirectory scan warnings:\n{error_text}\n"
        if not text:
            text = "No file differences."
        if max_chars is not None and len(text) > max_chars:
            omitted = len(text) - max_chars
            return text[:max_chars] + f"\n\n... diff preview truncated, {omitted} characters omitted ..."
        return text

    def summary(self, result: Dict[str, Any]) -> str:
        return (
            f"旧工程: {result['base_dir']}\n"
            f"新工程: {result['target_dir']}\n"
            f"新增: {len(result['added'])}  删除: {len(result['removed'])}  "
            f"修改: {len(result['modified'])}  改名: {len(result.get('renamed', []))}  "
            f"相同: {result['same_count']}  "
            f"扫描警告: {len(result['errors'])}"
        )

    def filter_result(
        self,
        result: Dict[str, Any],
        status_filter: str = "all",
        file_type_filter: str = "all",
        filename_filter: str = "",
        extensions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        keyword = filename_filter.strip().casefold()
        normalized_extensions = {
            extension.casefold() if extension.startswith(".") else f".{extension.casefold()}"
            for extension in (extensions or [])
            if extension.strip()
        }

        def type_matches(relative_path):
            if file_type_filter != "all" and self.file_type(relative_path) != file_type_filter:
                return False
            if keyword and keyword not in relative_path.casefold():
                return False
            if normalized_extensions and os.path.splitext(relative_path)[1].casefold() not in normalized_extensions:
                return False
            return True

        filtered = dict(result)
        filtered["added"] = [
            path for path in result["added"]
            if status_filter in {"all", "added"} and type_matches(path)
        ]
        filtered["removed"] = [
            path for path in result["removed"]
            if status_filter in {"all", "removed"} and type_matches(path)
        ]
        filtered["modified"] = [
            item for item in result["modified"]
            if status_filter in {"all", "modified"} and type_matches(item["path"])
        ]
        filtered["renamed"] = [
            item for item in result.get("renamed", [])
            if status_filter in {"all", "renamed"} and type_matches(item["to"])
        ]
        return filtered

    @staticmethod
    def file_type(relative_path: str) -> str:
        filename = os.path.basename(relative_path).casefold()
        extension = os.path.splitext(filename)[1]
        if extension in HEADER_EXTENSIONS:
            return "header"
        if extension in SOURCE_EXTENSIONS:
            return "source"
        if extension in PROJECT_EXTENSIONS or filename in {"makefile", "cmakelists.txt"}:
            return "project"
        if extension in DOCUMENT_EXTENSIONS:
            return "document"
        if extension in BINARY_EXTENSIONS:
            return "binary"
        return "other"

    def save_report(self, result: Dict[str, Any], output_path: str) -> str:
        report = self.summary(result) + "\n\n" + self.build_diff(result)
        parent = os.path.dirname(os.path.abspath(output_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="\n") as file:
            file.write(report)
        return output_path

    def _validate(self) -> None:
        if not os.path.isdir(self.base_dir):
            raise FileNotFoundError(f"旧工程目录不存在：{self.base_dir}")
        if not os.path.isdir(self.target_dir):
            raise FileNotFoundError(f"新工程目录不存在：{self.target_dir}")
        if os.path.normcase(self.base_dir) == os.path.normcase(self.target_dir):
            raise ValueError("旧工程和新工程不能是同一个目录。")
        try:
            common = os.path.normcase(os.path.commonpath([self.base_dir, self.target_dir]))
        except ValueError:
            common = ""
        if common in {os.path.normcase(self.base_dir), os.path.normcase(self.target_dir)}:
            raise ValueError("旧工程和新工程不能互相包含，请选择两个独立工程目录。")

    def _scan(
        self,
        root: str,
        cancel_token: Optional[CancellationToken] = None,
        progress_callback=None,
    ) -> Tuple[Dict[str, str], List[str]]:
        files = {}
        errors = []
        def on_error(exc):
            errors.append(str(exc))

        for current_root, dirnames, filenames in os.walk(root, topdown=True, onerror=on_error, followlinks=False):
            self._check(cancel_token)
            dirnames[:] = [
                name for name in dirnames
                if not self._is_excluded_dir(root, current_root, name)
            ]
            for filename in filenames:
                self._check(cancel_token)
                full_path = os.path.join(current_root, filename)
                relative_path = os.path.relpath(full_path, root).replace("\\", "/")
                if self._is_excluded(relative_path, filename):
                    continue
                if os.path.isfile(full_path):
                    files[relative_path] = full_path
        return files, errors

    def _detect_renames(
        self,
        added,
        removed,
        base_files,
        target_files,
        cancel_token,
        progress_callback,
    ):
        removed_by_signature = {}
        candidates = [("removed", path) for path in removed] + [("added", path) for path in added]
        added_signatures = {}
        for index, (kind, path) in enumerate(candidates, 1):
            self._check(cancel_token)
            self._progress(
                progress_callback,
                55 + int(15 * index / max(len(candidates), 1)),
                f"正在识别改名文件（{index}/{len(candidates)}）",
            )
            full_path = base_files[path] if kind == "removed" else target_files[path]
            signature = (os.path.getsize(full_path), self._sha256(full_path, cancel_token))
            if kind == "removed":
                removed_by_signature.setdefault(signature, []).append(path)
            else:
                added_signatures[path] = signature

        renamed = []
        matched_added = set()
        matched_removed = set()
        for added_path in added:
            signature = added_signatures.get(added_path)
            candidates_for_signature = removed_by_signature.get(signature, [])
            if not candidates_for_signature:
                continue
            removed_path = candidates_for_signature.pop(0)
            matched_added.add(added_path)
            matched_removed.add(removed_path)
            renamed.append({
                "from": removed_path,
                "to": added_path,
                "size": signature[0],
                "sha256": signature[1],
            })
        return (
            [path for path in added if path not in matched_added],
            [path for path in removed if path not in matched_removed],
            sorted(renamed, key=lambda item: item["to"].casefold()),
        )

    def _is_excluded_dir(self, root: str, current_root: str, dirname: str) -> bool:
        full_path = os.path.join(current_root, dirname)
        relative_path = os.path.relpath(full_path, root).replace("\\", "/").strip("/")
        return dirname.casefold() in self.exclude_dirs or relative_path.casefold() in self.exclude_dirs

    def _is_excluded(self, relative_path: str, filename: str) -> bool:
        normalized = relative_path.replace("\\", "/")
        return any(
            fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(normalized, pattern)
            for pattern in self.exclude_patterns
        )

    @staticmethod
    def _sha256(path: str, cancel_token: Optional[CancellationToken] = None) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                if cancel_token:
                    cancel_token.check()
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _is_text_path(relative_path: str) -> bool:
        filename = os.path.basename(relative_path)
        extension = os.path.splitext(filename)[1].casefold()
        return extension in TEXT_EXTENSIONS or filename.casefold() in {"makefile", "cmakelists.txt"}

    def _file_diff(
        self,
        relative_path: str,
        status: str,
        base_path: Optional[str],
        target_path: Optional[str],
        base_relative_path: Optional[str] = None,
        cancel_token: Optional[CancellationToken] = None,
    ) -> str:
        self._check(cancel_token)
        base_label = base_relative_path or relative_path
        header = [
            f"diff --git a/{base_label} b/{relative_path}",
            f"status {status}",
        ]
        if not self._is_text_path(relative_path):
            base_size, base_hash = self._binary_info(base_path, cancel_token)
            target_size, target_hash = self._binary_info(target_path, cancel_token)
            header.extend([
                f"binary base size={base_size} sha256={base_hash}",
                f"binary target size={target_size} sha256={target_hash}",
                "Binary files differ",
            ])
            return "\n".join(header)

        base_lines = self._read_text_lines(base_path) if base_path else []
        target_lines = self._read_text_lines(target_path) if target_path else []
        diff_lines = difflib.unified_diff(
            base_lines,
            target_lines,
            fromfile=f"a/{base_label}" if base_path else "/dev/null",
            tofile=f"b/{relative_path}" if target_path else "/dev/null",
            lineterm="",
        )
        header.extend(diff_lines)
        return "\n".join(header)

    def _binary_info(
        self,
        path: Optional[str],
        cancel_token: Optional[CancellationToken] = None,
    ) -> Tuple[int, str]:
        if not path:
            return 0, "-"
        return os.path.getsize(path), self._sha256(path, cancel_token)

    @staticmethod
    def _read_text_lines(path: str) -> List[str]:
        with open(path, "rb") as file:
            data = file.read()
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                return data.decode(encoding).splitlines()
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace").splitlines()

    @staticmethod
    def _check(cancel_token: Optional[CancellationToken]) -> None:
        if cancel_token:
            cancel_token.check()

    def _progress(self, progress_callback, percent: int, message: str) -> None:
        if not progress_callback or percent == self._last_progress_percent:
            return
        self._last_progress_percent = percent
        progress_callback(percent, message)
