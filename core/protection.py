import base64
import hashlib
import hmac
import os
import subprocess
from typing import Optional

try:
    from core.subprocess_utils import hidden_subprocess_kwargs
except ModuleNotFoundError:
    from stm32_git_release_tool.core.subprocess_utils import hidden_subprocess_kwargs


def hash_password(password: str, salt: Optional[bytes] = None) -> dict:
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return {
        "password_salt": base64.b64encode(salt).decode("ascii"),
        "password_hash": base64.b64encode(digest).decode("ascii"),
    }


def verify_password(password: str, config: dict) -> bool:
    encoded_salt = config.get("password_salt", "")
    encoded_hash = config.get("password_hash", "")
    if not encoded_salt or not encoded_hash:
        return False
    salt = base64.b64decode(encoded_salt.encode("ascii"))
    expected = base64.b64decode(encoded_hash.encode("ascii"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return hmac.compare_digest(actual, expected)


def protection_enabled(config: dict) -> bool:
    return bool(config.get("protection_enabled") and config.get("password_hash"))


def protect_repository_dirs(project_path: str, log=None) -> None:
    """Mark Git/tool metadata folders as hidden on Windows to reduce accidental deletion."""
    set_repository_dirs_hidden(project_path, True, log)


def show_repository_dirs(project_path: str, log=None) -> None:
    """Make Git/tool metadata folders visible on Windows."""
    set_repository_dirs_hidden(project_path, False, log)


def set_repository_dirs_hidden(project_path: str, hidden: bool, log=None) -> None:
    if os.name != "nt":
        return
    flags = ["+h", "+s"] if hidden else ["-h", "-s"]
    action = "设置目录隐藏属性" if hidden else "取消目录隐藏属性"
    for dirname in [".git", ".stm32_git_tool"]:
        path = os.path.join(project_path, dirname)
        if not os.path.isdir(path):
            continue
        try:
            subprocess.run(
                ["attrib", *flags, path],
                capture_output=True,
                text=True,
                timeout=5,
                **hidden_subprocess_kwargs(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            if log:
                log(f"[提示] 无法{action} {path}: {exc}")


def repository_dirs_hidden(project_path: str) -> bool:
    git_path = os.path.join(project_path, ".git")
    if os.name != "nt" or not os.path.exists(git_path):
        return False
    try:
        completed = subprocess.run(
            ["attrib", git_path],
            capture_output=True,
            text=True,
            timeout=5,
            **hidden_subprocess_kwargs(),
        )
        attributes = completed.stdout.split(maxsplit=1)[0].upper()
        return "H" in attributes
    except (OSError, subprocess.SubprocessError):
        return False


def ensure_writable_file(path: str, log=None) -> None:
    """Clear read-only/hidden/system attributes before updating a project file."""
    if not os.path.exists(path):
        return
    try:
        os.chmod(path, 0o666)
    except OSError as exc:
        if log:
            log(f"[提示] 无法修改文件写权限 {path}: {exc}")
    if os.name != "nt":
        return
    try:
        subprocess.run(
            ["attrib", "-r", "-s", "-h", path],
            capture_output=True,
            text=True,
            timeout=5,
            **hidden_subprocess_kwargs(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        if log:
            log(f"[提示] 无法清除文件属性 {path}: {exc}")
