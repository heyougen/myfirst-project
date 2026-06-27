import os
import platform
import shutil
import zipfile
from datetime import datetime
from typing import Dict, List

try:
    from core.tool_paths import tool_file
except ModuleNotFoundError:
    from stm32_git_release_tool.core.tool_paths import tool_file


class Diagnostics:
    def __init__(self, project_path: str, git_service, config: Dict):
        self.project_path = project_path
        self.git = git_service
        self.config = config

    def health_report(self) -> str:
        lines: List[str] = []
        lines.append("工程健康检查")
        lines.append("=" * 40)
        lines.append(f"工程路径: {self.project_path}")
        lines.append(f"系统: {platform.platform()}")
        lines.append("")

        if not os.path.isdir(self.project_path):
            lines.append("[失败] 工程路径不存在。")
            return "\n".join(lines)

        if not self.git.is_repository():
            lines.append("[失败] 当前目录不是 Git 仓库。建议点击“初始化工程”。")
            return "\n".join(lines)

        branch = self.git.current_branch()
        tag = self.git.current_tag() or "-"
        meaningful = self.git.meaningful_changed_files()
        tags = self.git.list_tags()
        remotes = self.git.run(["remote", "-v"]).stdout.strip()

        lines.append(f"[通过] Git 仓库已就绪")
        lines.append(f"当前分支: {branch}")
        lines.append(f"当前 tag: {tag}")
        lines.append(f"tag 数量: {len(tags)}")
        lines.append(f"有效工程改动: {len(meaningful)} 个")
        if meaningful:
            for item in meaningful[:30]:
                lines.append(f"  - {item}")
            if len(meaningful) > 30:
                lines.append(f"  ... 另有 {len(meaningful) - 30} 个")

        if branch == "(detached)":
            lines.append("[警告] 当前处于历史查看模式 detached HEAD。建议点击“返回分支”。")

        if remotes:
            lines.append("[通过] 已配置远程仓库")
            lines.append(remotes)
        else:
            lines.append("[提示] 未配置远程仓库。")

        firmware_files = self.find_firmware_files()
        lines.append(f"固件/产物文件: {len(firmware_files)} 个")
        for item in firmware_files[:20]:
            lines.append(f"  - {item}")

        missing_ignore = self.missing_ignore_rules()
        if missing_ignore:
            lines.append("[提示] .gitignore 缺少建议规则:")
            for item in missing_ignore:
                lines.append(f"  - {item}")
        else:
            lines.append("[通过] .gitignore 包含关键忽略规则")

        return "\n".join(lines)

    def find_firmware_files(self) -> List[str]:
        patterns = self.config.get("firmware_patterns", ["*.bin", "*.hex"])
        matches = []
        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if d not in {".git", ".stm32_git_tool", "releases", "diff_reports"}]
            for name in files:
                lower = name.lower()
                if any(self._match_pattern(lower, pattern.lower()) for pattern in patterns):
                    matches.append(os.path.join(root, name))
        return matches

    @staticmethod
    def _match_pattern(name: str, pattern: str) -> bool:
        if pattern.startswith("*."):
            return name.endswith(pattern[1:])
        return name == pattern

    def missing_ignore_rules(self) -> List[str]:
        required = [".stm32_git_tool/", "*.uvguix.*", "*.build_log.htm"]
        gitignore_path = os.path.join(self.project_path, ".gitignore")
        if not os.path.exists(gitignore_path):
            return required
        with open(gitignore_path, "r", encoding="utf-8", errors="replace") as file:
            content = file.read()
        return [rule for rule in required if rule not in content]

    def export_diagnostics(self, app_log_path: str = "") -> str:
        out_dir = tool_file(self.project_path, "diagnostics")
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(out_dir, f"health_{stamp}.txt")
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(self.health_report())

        zip_path = os.path.join(out_dir, f"diagnostics_{stamp}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(report_path, os.path.basename(report_path))
            config_path = tool_file(self.project_path, "app_config.json")
            if os.path.exists(config_path):
                archive.write(config_path, "app_config.json")
            gitignore_path = os.path.join(self.project_path, ".gitignore")
            if os.path.exists(gitignore_path):
                archive.write(gitignore_path, ".gitignore")
            if app_log_path and os.path.exists(app_log_path):
                archive.write(app_log_path, os.path.join("logs", os.path.basename(app_log_path)))
        return zip_path
