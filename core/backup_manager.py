from datetime import datetime


class BackupManager:
    def __init__(self, git_service):
        self.git = git_service

    def create_backup(self, reason: str = "manual") -> str:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_reason = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in reason)
        name = f"backup/{safe_reason}-{stamp}"
        self.git.run(["branch", name, "HEAD"], check=True)
        return name

    def list_backups(self) -> list[str]:
        branches = self.git.list_branches()
        return [branch for branch in branches if branch.startswith("backup/")]

    def checkout_backup(self, name: str):
        return self.git.checkout_branch(name)

    def reset_to_backup(self, name: str):
        return self.git.reset_hard(name)

    def delete_backup(self, name: str):
        return self.git.delete_branch(name, force=True)
