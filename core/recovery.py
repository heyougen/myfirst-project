import os
import subprocess

try:
    from core.subprocess_utils import hidden_subprocess_kwargs
except ModuleNotFoundError:
    from stm32_git_release_tool.core.subprocess_utils import hidden_subprocess_kwargs


class Recovery:
    @staticmethod
    def clone(remote_url: str, parent_dir: str, target_name: str = "") -> str:
        if not remote_url.strip():
            raise RuntimeError("远程仓库地址为空")
        if not os.path.isdir(parent_dir):
            raise RuntimeError("目标父目录不存在")
        cmd = ["git", "clone", remote_url.strip()]
        if target_name.strip():
            cmd.append(target_name.strip())
            target_path = os.path.join(parent_dir, target_name.strip())
        else:
            target_path = os.path.join(parent_dir, os.path.splitext(os.path.basename(remote_url.rstrip("/")))[0])
        completed = subprocess.run(
            cmd,
            cwd=parent_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            **hidden_subprocess_kwargs(),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "git clone 失败")
        return target_path
