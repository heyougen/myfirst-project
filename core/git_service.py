import os
import subprocess
import fnmatch
import locale
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

try:
    from core.git_errors import humanize_git_error
    from core.subprocess_utils import hidden_subprocess_kwargs
    from core.tool_paths import tool_file
except ModuleNotFoundError:
    from stm32_git_release_tool.core.git_errors import humanize_git_error
    from stm32_git_release_tool.core.subprocess_utils import hidden_subprocess_kwargs
    from stm32_git_release_tool.core.tool_paths import tool_file


LogCallback = Optional[Callable[[str], None]]


@dataclass
class GitResult:
    command: List[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class GitService:
    """Small Git command wrapper used by the UI layer."""

    def __init__(self, project_path: str, log: LogCallback = None):
        self.project_path = project_path
        self.log = log
        self.timeout_seconds = 180

    def set_project_path(self, project_path: str) -> None:
        self.project_path = project_path

    def _log(self, message: str) -> None:
        if self.log:
            self.log(message)

    def _check_path(self) -> None:
        if not self.project_path or not os.path.isdir(self.project_path):
            raise FileNotFoundError("工程路径不存在或未选择")

    @staticmethod
    def decode_output(data: bytes) -> str:
        encodings = ["utf-8", locale.getpreferredencoding(False), "gbk", "cp936"]
        seen = set()
        for encoding in encodings:
            if not encoding or encoding.lower() in seen:
                continue
            seen.add(encoding.lower())
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="replace")

    def run(self, args: List[str], check: bool = False) -> GitResult:
        self._check_path()
        cmd = ["git"] + args
        command_line = subprocess.list2cmdline(cmd)
        self._log(f"> {command_line}")

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "Never"

        try:
            completed = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                env=env,
                timeout=self.timeout_seconds,
                **hidden_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired as exc:
            message = f"Git 命令超时：{command_line}"
            self._log(f"[超时] {message}")
            stdout = self.decode_output(exc.stdout or b"") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = self.decode_output(exc.stderr or b"") if isinstance(exc.stderr, bytes) else (exc.stderr or message)
            result = GitResult(cmd, 124, stdout, stderr)
            if check:
                raise RuntimeError(humanize_git_error(message))
            return result
        except PermissionError as exc:
            self._log(f"[权限错误] {exc}")
            raise PermissionError(humanize_git_error(str(exc))) from exc
        except FileNotFoundError as exc:
            self._log("[错误] 未找到 git，请确认 Git 已安装并加入 PATH")
            raise exc

        stdout = self.decode_output(completed.stdout or b"")
        stderr = self.decode_output(completed.stderr or b"")
        if stdout.strip():
            self._log(stdout.strip())
        if stderr.strip():
            self._log(stderr.strip())
        self._log("[成功]" if completed.returncode == 0 else f"[失败] return code: {completed.returncode}")

        result = GitResult(cmd, completed.returncode, stdout, stderr)
        if check and not result.ok:
            raise RuntimeError(humanize_git_error(result.stderr.strip() or result.stdout.strip() or "Git 命令执行失败"))
        return result

    def run_preview(self, args: List[str], max_chars: int = 120000) -> str:
        self._check_path()
        cmd = ["git"] + args
        command_line = subprocess.list2cmdline(cmd)
        self._log(f"> {command_line}  [preview]")

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "Never"

        output_parts: List[str] = []
        total = 0
        truncated = False
        try:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                **hidden_subprocess_kwargs(),
            )
            assert process.stdout is not None
            raw_parts: List[bytes] = []
            while True:
                chunk = process.stdout.read(4096)
                if not chunk:
                    break
                remaining = max_chars - total
                if remaining > 0:
                    raw_parts.append(chunk[:remaining])
                    total += min(len(chunk), remaining)
                if total >= max_chars:
                    truncated = True
                    process.kill()
                    break
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            truncated = True
            process.kill()
        except FileNotFoundError as exc:
            raise exc

        text = self.decode_output(b"".join(raw_parts))
        if truncated:
            text += (
                "\n\n[DIFF_TRUNCATED] Diff 内容过大，预览已在 "
                + str(max_chars)
                + " 个字符处停止。请使用“保存完整 Diff”导出 patch 文件查看全部内容。\n"
            )
        self._log("[成功] diff 预览已生成" + ("，内容已截断" if truncated else ""))
        return text

    def save_command_output(self, args: List[str], output_path: str) -> str:
        self._check_path()
        cmd = ["git"] + args
        command_line = subprocess.list2cmdline(cmd)
        self._log(f"> {command_line}  > {output_path}")

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GCM_INTERACTIVE"] = "Never"

        with open(output_path, "w", encoding="utf-8", errors="replace") as file:
            completed = subprocess.run(
                cmd,
                cwd=self.project_path,
                stdout=file,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=self.timeout_seconds,
                **hidden_subprocess_kwargs(),
            )
        if completed.returncode != 0:
            raise RuntimeError(humanize_git_error(f"保存 diff 失败，return code: {completed.returncode}"))
        self._log(f"[成功] 完整 Diff 已保存：{output_path}")
        return output_path

    def is_repository(self) -> bool:
        if not self.project_path or not os.path.isdir(self.project_path):
            return False
        return os.path.isdir(os.path.join(self.project_path, ".git"))

    def init_project(self) -> None:
        self.run(["init"], check=True)

    def add_all(self) -> None:
        self.run(["add", "."], check=True)

    def add_paths(self, paths: List[str]) -> None:
        for path in paths:
            self.run(["add", "--", path], check=True)

    def commit(self, message: str) -> GitResult:
        return self.run(["commit", "-m", message])

    def tag(self, version: str) -> GitResult:
        return self.run(["tag", version], check=True)

    def delete_tag(self, version: str) -> GitResult:
        return self.run(["tag", "-d", version], check=True)

    def resolve_commit(self, ref: str) -> str:
        result = self.run(["rev-parse", f"{ref}^{{commit}}"], check=True)
        return result.stdout.strip()

    def commit_has_parent(self, ref: str) -> bool:
        return self.run(["rev-parse", "--verify", f"{ref}^"]).ok

    def remote_branches_containing(self, ref: str) -> List[str]:
        result = self.run(["branch", "-r", "--contains", ref])
        return [
            line.replace("*", "").strip()
            for line in result.stdout.splitlines()
            if line.replace("*", "").strip()
        ]

    def checkout(self, ref: str) -> GitResult:
        return self.run(["checkout", ref])

    def checkout_force(self, ref: str) -> GitResult:
        return self.run(["checkout", "-f", ref])

    def reset_hard(self, ref: str) -> GitResult:
        return self.run(["reset", "--hard", ref], check=True)

    def reset_hard_attached(self, ref: str, detached_branch_name: str) -> GitResult:
        if self.current_branch() == "(detached)":
            self.create_and_checkout_branch(detached_branch_name)
        return self.reset_hard(ref)

    def pull(self) -> GitResult:
        return self.run(["pull"], check=True)

    def push(self, push_tags: bool = False) -> GitResult:
        result = self.run(["push"], check=True)
        if push_tags and result.ok:
            return self.run(["push", "--tags"], check=True)
        return result

    def cleanup_history_cache(self) -> GitResult:
        self.run(["reflog", "expire", "--expire=now", "--all"], check=True)
        return self.run(["gc", "--prune=now"], check=True)

    def status_porcelain(self) -> str:
        return self.run(["status", "--porcelain", "-uall"], check=True).stdout

    def has_changes(self) -> bool:
        return bool(self.status_porcelain().strip())

    def changed_files(self) -> List[str]:
        return [line.rstrip() for line in self.status_porcelain().splitlines() if line.strip()]

    @staticmethod
    def status_path(status_line: str) -> str:
        text = status_line[3:] if len(status_line) > 3 else status_line
        if " -> " in text:
            text = text.split(" -> ", 1)[1]
        return text.strip().strip('"').replace("\\", "/")

    @staticmethod
    def is_noise_path(path: str) -> bool:
        normalized = path.replace("\\", "/")
        name = os.path.basename(normalized)
        patterns = [
            "Debug/*",
            "Objects/*",
            "Listings/*",
            "MDK-ARM/Debug/*",
            "MDK-ARM/Objects/*",
            "MDK-ARM/Listings/*",
            "releases/*",
            "diff_reports/*",
            "diagnostics/*",
            "logs/*",
            ".stm32_git_tool/*",
            "app_config.json",
            ".git_guard.json",
            "*.map",
            "*.axf",
            "*.hex",
            "*.bin",
            "*.crf",
            "*.elf",
            "*.lib",
            "*.a",
            "*.o",
            "*.d",
            "*.obj",
            "*.lst",
            "*.dep",
            "*.lnp",
            "*.htm",
            "*.build_log.htm",
            "*.uvguix.*",
            "*.uvguix",
            "*.uvgui.*",
            "*.uvgui",
        ]
        return any(fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(name, pattern) for pattern in patterns)

    @staticmethod
    def is_code_diff_path(path: str) -> bool:
        normalized = path.replace("\\", "/")
        name = os.path.basename(normalized)
        if GitService.is_noise_path(normalized):
            return False
        excluded_patterns = [
            "*.hex",
            "*.bin",
            "*.crf",
            "*.elf",
            "*.lib",
            "*.a",
            "*.lst",
            "*.map",
            "*.axf",
            "*.o",
            "*.d",
            "*.htm",
            "*.html",
        ]
        if any(fnmatch.fnmatch(name.lower(), pattern) for pattern in excluded_patterns):
            return False
        included_patterns = [
            "*.c",
            "*.h",
            "*.cpp",
            "*.hpp",
            "*.cc",
            "*.s",
            "*.asm",
            "*.ld",
            "*.txt",
            "*.md",
            "*.ioc",
            "*.uvprojx",
            "*.uvoptx",
            "*.uvproj",
            "*.uvopt",
            "*.xml",
            "*.json",
            "*.ini",
            "*.cfg",
            "*.py",
        ]
        return any(fnmatch.fnmatch(name.lower(), pattern) for pattern in included_patterns)

    def changed_code_files_in_commit(self, ref: str) -> List[str]:
        result = self.run(["show", "--name-only", "--pretty=format:", ref], check=True)
        files = []
        for line in result.stdout.splitlines():
            path = line.strip()
            if path and self.is_code_diff_path(path):
                files.append(path)
        return files

    def changed_code_files_between(self, base_ref: str, target_ref: str) -> List[str]:
        result = self.run(["diff", "--name-only", f"{base_ref}..{target_ref}"], check=True)
        files = []
        for line in result.stdout.splitlines():
            path = line.strip()
            if path and self.is_code_diff_path(path):
                files.append(path)
        return files

    def meaningful_changed_files(self) -> List[str]:
        paths = []
        for line in self.changed_files():
            path = self.status_path(line)
            if path and not self.is_noise_path(path):
                paths.append(path)
        return paths

    def has_staged_changes(self) -> bool:
        result = self.run(["diff", "--cached", "--quiet"])
        return result.returncode == 1

    def current_branch(self) -> str:
        result = self.run(["branch", "--show-current"])
        return result.stdout.strip() or "(detached)"

    def current_tag(self) -> str:
        result = self.run(["describe", "--tags", "--exact-match"])
        return result.stdout.strip() if result.ok else ""

    def list_tags(self) -> List[str]:
        result = self.run(["tag", "--sort=-creatordate"])
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def list_compare_refs(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        head_result = self.run([
            "log",
            "-1",
            "--date=format-local:%Y-%m-%d %H:%M",
            "--pretty=format:%ad%x09%s",
            "HEAD",
        ])
        head_label = "HEAD"
        if head_result.ok and head_result.stdout.strip():
            parts = head_result.stdout.strip().split("\t", 1)
            head_details = "  ".join(part for part in parts if part)
            if head_details:
                head_label = f"HEAD ({head_details})"
        refs = [{"label": head_label, "ref": "HEAD", "kind": "head"}]
        tag_format = (
            "%(refname:short)%09%(creatordate:format-local:%Y-%m-%d %H:%M)%09"
            "%(if)%(*subject)%(then)%(*subject)%(else)%(subject)%(end)"
        )
        tag_result = self.run([
            "for-each-ref",
            "--sort=-creatordate",
            f"--format={tag_format}",
            "refs/tags",
        ])
        for line in tag_result.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            tag, date, subject = parts
            label = f"tag: {tag}  {date}"
            if subject:
                label += f"  {subject}"
            refs.append({"label": label, "ref": tag, "kind": "tag"})

        fmt = "%H%x09%ad%x09%s"
        command = ["log", "--all", "--date=format-local:%Y-%m-%d %H:%M", f"--pretty=format:{fmt}"]
        if limit is not None:
            command.insert(2, f"--max-count={limit}")
        result = self.run(command)
        for line in result.stdout.splitlines():
            parts = line.split("\t", 2)
            if len(parts) != 3:
                continue
            full_hash, date, subject = parts
            refs.append({
                "label": f"commit: {date}  {subject}",
                "ref": full_hash,
                "kind": "commit",
            })
        return refs

    def list_branches(self) -> List[str]:
        result = self.run(["branch", "--list"])
        branches = []
        for line in result.stdout.splitlines():
            branch = line.replace("*", "").strip()
            if branch.startswith("(HEAD detached"):
                continue
            branches.append(branch)
        return [branch for branch in branches if branch]

    def create_branch(self, name: str) -> GitResult:
        return self.run(["branch", name])

    def create_and_checkout_branch(self, name: str) -> GitResult:
        return self.run(["checkout", "-b", name], check=True)

    def checkout_branch(self, name: str) -> GitResult:
        return self.run(["checkout", name])

    def delete_branch(self, name: str, force: bool = False) -> GitResult:
        return self.run(["branch", "-D" if force else "-d", name])

    def merge_branch(self, name: str) -> GitResult:
        return self.run(["merge", name])

    def commit_history(self, limit: Optional[int] = None) -> str:
        fmt = "%h%x09%ad%x09%d%x09%s"
        command = ["log", "--all", "--date=short", f"--pretty=format:{fmt}"]
        if limit is not None:
            command.insert(2, f"--max-count={limit}")
        return self.run(command).stdout

    def diff(self, ref: Optional[str] = None) -> str:
        if ref:
            return self.run(["show", "--stat", "--patch", ref]).stdout
        return self.run(["diff"]).stdout

    def diff_between(self, base_ref: str, target_ref: str) -> str:
        return self.run(["diff", f"{base_ref}..{target_ref}"]).stdout

    @staticmethod
    def preview_text(text: str, max_chars: int = 120000) -> str:
        if len(text) <= max_chars:
            return text
        omitted = len(text) - max_chars
        return (
            text[:max_chars]
            + "\n\n[DIFF_TRUNCATED] 内容过大，界面仅显示前 "
            + str(max_chars)
            + " 个字符，已省略 "
            + str(omitted)
            + " 个字符。请使用“保存完整 Diff”查看全部内容。]\n"
        )

    def diff_preview(self, ref: Optional[str] = None, max_chars: int = 120000) -> str:
        if ref:
            return self.run_preview(["show", "--stat", "--patch", ref], max_chars=max_chars)
        return self.run_preview(["diff"], max_chars=max_chars)

    def diff_between_preview(self, base_ref: str, target_ref: str, max_chars: int = 120000) -> str:
        return self.run_preview(["diff", f"{base_ref}..{target_ref}"], max_chars=max_chars)

    def code_diff_preview(self, ref: str, max_chars: int = 120000) -> str:
        files = self.changed_code_files_in_commit(ref)
        if not files:
            return "这次提交没有源码/工程配置差异；只有固件、编译产物或缓存文件变化。"
        return self._code_diff_preview_for_files(["show", "--format=", "--patch", "-w"], files, max_chars=max_chars)

    def code_diff_between_preview(self, base_ref: str, target_ref: str, max_chars: int = 120000) -> str:
        files = self.changed_code_files_between(base_ref, target_ref)
        if not files:
            return "这两个版本之间没有源码/工程配置差异；只有固件、编译产物或缓存文件变化。"
        return self._code_diff_preview_for_files(["diff", "-w", f"{base_ref}..{target_ref}"], files, max_chars=max_chars)

    def _code_diff_preview_for_files(self, base_args: List[str], files: List[str], max_chars: int = 120000) -> str:
        max_files = 300
        selected_files = files[:max_files]
        parts: List[str] = []
        total = 0

        if len(files) > max_files:
            notice = (
                f"[DIFF_FILE_LIMIT] 本次变更文件过多，仅预览前 {max_files} 个源码/工程配置文件。"
                "请使用“保存完整 Diff”导出完整 patch。\n\n"
            )
            parts.append(notice)
            total += len(notice)

        self._log(f"[Diff] 逐文件生成预览，文件数: {len(selected_files)} / {len(files)}")
        for path in selected_files:
            remaining = max_chars - total
            if remaining <= 0:
                parts.append("\n\n[DIFF_TRUNCATED] Diff 内容过大，预览已截断。请使用“保存完整 Diff”导出完整 patch。\n")
                break
            try:
                text = self.run_preview(base_args + ["--", path], max_chars=remaining)
            except OSError as exc:
                text = f"diff --git a/{path} b/{path}\n[DIFF_SKIPPED] 无法读取该文件差异：{exc}\n"
            if text.strip():
                chunk = text.rstrip() + "\n"
                parts.append(chunk)
                total += len(chunk)

        return "\n".join(parts).strip() or "没有可显示的代码差异。"

    def save_diff_between(self, base_ref: str, target_ref: str, output_dir: Optional[str] = None) -> str:
        if output_dir is None:
            output_dir = tool_file(self.project_path, "diff_reports")
        os.makedirs(output_dir, exist_ok=True)
        safe_base = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base_ref)
        safe_target = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in target_ref)
        path = os.path.join(output_dir, f"diff_{safe_base}_to_{safe_target}.patch")
        return self.save_command_output(["diff", f"{base_ref}..{target_ref}"], path)

    def save_diff(self, ref: str, output_dir: Optional[str] = None) -> str:
        if output_dir is None:
            output_dir = tool_file(self.project_path, "diff_reports")
        os.makedirs(output_dir, exist_ok=True)
        safe_ref = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in ref)
        path = os.path.join(output_dir, f"diff_{safe_ref}.patch")
        return self.save_command_output(["show", "--stat", "--patch", ref], path)

    def diff_stat_between(self, base_ref: str, target_ref: str) -> str:
        return self.run(["diff", "--stat", f"{base_ref}..{target_ref}"]).stdout

    def commits_between(self, base_ref: str, target_ref: str) -> str:
        fmt = "%h%x09%ad%x09%s"
        return self.run(
            ["log", f"{base_ref}..{target_ref}", "--date=short", f"--pretty=format:{fmt}"]
        ).stdout

    def revert_commit(self, commit_hash: str) -> GitResult:
        return self.run(["revert", "--no-edit", commit_hash])

    def reset_hard_commit(self, commit_hash: str) -> GitResult:
        return self.run(["reset", "--hard", commit_hash], check=True)
