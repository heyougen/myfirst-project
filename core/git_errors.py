try:
    from core.i18n import tr
except ModuleNotFoundError:
    from stm32_git_release_tool.core.i18n import tr


def humanize_git_error(message: str) -> str:
    text = (message or "").strip()
    lower = text.lower()
    if not text:
        return tr("Git 命令执行失败。")

    if "please tell me who you are" in lower or "user.email" in lower or "user.name" in lower:
        cmds = 'git config --global user.name "your name"\ngit config --global user.email "your email"'
        return tr("Git 用户信息未配置。\n\n请在 PowerShell 执行：\n{cmds}", cmds=cmds)
    if "detected dubious ownership" in lower or "safe.directory" in lower:
        return tr("Git 认为当前工程目录归属异常，已阻止操作。\n\n请把该工程目录加入 Git 安全目录，或换当前用户拥有的目录。")
    if "already exists" in lower and "tag" in lower:
        return tr("该版本 tag 已存在。请换一个版本号，或先确认是否已经发布过该版本。")
    if "nothing to commit" in lower or "no changes added to commit" in lower:
        return tr("没有可提交的有效工程改动。")
    if "permission denied" in lower or "access is denied" in lower:
        return tr("权限不足。请检查文件是否被占用、是否只读，或当前账号是否有工程目录写权限。")
    if "could not read from remote repository" in lower or "repository not found" in lower:
        return tr("远程仓库无法访问。请检查远程地址、网络、账号权限和 SSH/Token 配置。")
    if "authentication failed" in lower or "403" in lower or "401" in lower:
        return tr("远程认证失败。请检查 Git 账号权限、Token 或 SSH Key。")
    if "failed to connect" in lower or "could not resolve host" in lower:
        return tr("网络连接失败。请检查网络、代理、DNS 或远程仓库地址。")
    if "your local changes" in lower and "would be overwritten" in lower:
        return tr("当前存在未提交修改，Git 为避免覆盖文件已阻止操作。请先提交、暂存或放弃修改。")
    if "not a git repository" in lower:
        return tr("当前目录不是 Git 仓库。请先选择正确工程目录，或点击“初始化工程”。")
    if "pathspec" in lower and "did not match" in lower:
        return tr("指定的分支、tag 或文件不存在。请刷新状态后重新选择。")
    if "filename or extension is too long" in lower or "winerror 206" in lower:
        return tr("路径或命令过长。工具已限制 Diff 预览；如果仍出现，请缩短工程路径或减少超深目录。")

    return text
