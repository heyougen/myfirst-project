from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

try:
    from core.i18n import tr
    from core.backup_manager import BackupManager
    from core.git_worker import TaskWorker
    from ui.help_widgets import make_help_box
except ModuleNotFoundError:
    from stm32_git_release_tool.core.i18n import tr
    from stm32_git_release_tool.core.backup_manager import BackupManager
    from stm32_git_release_tool.core.git_worker import TaskWorker
    from stm32_git_release_tool.ui.help_widgets import make_help_box


class BackupDialog(QDialog):
    def __init__(self, git_service, refresh_callback, verify_callback=None, parent=None):
        super().__init__(parent)
        self.git = git_service
        self.manager = BackupManager(git_service)
        self.refresh_callback = refresh_callback
        self.verify_callback = verify_callback
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle(tr("备份分支管理"))
        self.resize(760, 420)

        self.list_widget = QListWidget()
        self.refresh_button = QPushButton(tr("刷新"))
        self.checkout_button = QPushButton(tr("查看备份"))
        self.restore_button = QPushButton(tr("恢复到备份"))
        self.delete_button = QPushButton(tr("删除备份"))
        self.buttons = [self.refresh_button, self.checkout_button, self.restore_button, self.delete_button]

        row = QHBoxLayout()
        for button in self.buttons:
            row.addWidget(button)
        row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("备份分支说明", [
            "备份列表：显示 backup/ 开头的分支。它们通常由工具在强制回退前自动创建。",
            "刷新按钮：重新读取备份分支列表。",
            "查看备份按钮：切换到选中的备份分支，只用于确认当时工程状态。查看后可回到原分支。",
            "恢复到备份按钮：执行 reset --hard 到选中的备份分支，会改变当前工程文件。执行前确认当前修改已处理。",
            "删除备份按钮：删除选中的 backup 分支。确认该备份不再需要后再删除。",
            "使用建议：强制回退后如果发现回退错了，优先到这里选择最近的 backup 分支进行恢复。",
        ]))
        layout.addWidget(self.list_widget)
        layout.addLayout(row)

        self.refresh_button.clicked.connect(self.load_backups)
        self.checkout_button.clicked.connect(self.checkout_backup)
        self.restore_button.clicked.connect(self.restore_backup)
        self.delete_button.clicked.connect(self.delete_backup)
        self.load_backups()

    def selected_backup(self):
        item = self.list_widget.currentItem()
        return item.text() if item else ""

    def set_busy(self, busy):
        for button in self.buttons:
            button.setEnabled(not busy)

    def run_async(self, func, on_finished=None):
        worker = TaskWorker(func)
        self.set_busy(True)
        worker.signals.error.connect(lambda text: QMessageBox.warning(self, tr("错误"), text))
        worker.signals.error.connect(lambda _: self.set_busy(False))
        worker.signals.finished.connect(lambda result: self.set_busy(False))
        if on_finished:
            worker.signals.finished.connect(on_finished)
        self.thread_pool.start(worker)

    def load_backups(self):
        def apply(backups):
            self.list_widget.clear()
            self.list_widget.addItems(backups)
        self.run_async(self.manager.list_backups, apply)

    def checkout_backup(self):
        name = self.selected_backup()
        if not name:
            return
        self.run_async(lambda: self.manager.checkout_backup(name), lambda _: self.refresh_callback())

    def restore_backup(self):
        name = self.selected_backup()
        if not name:
            return
        if QMessageBox.question(self, tr("确认恢复"), f"reset --hard -> {name}?") != QMessageBox.Yes:
            return
        if self.verify_callback and not self.verify_callback(tr("恢复到备份分支")):
            return

        def after_dirty(changes):
            if changes:
                QMessageBox.warning(self, tr("存在未提交修改"), tr("请先提交、暂存或放弃当前修改后再恢复备份。"))
                return
            self.run_async(lambda: self.restore_with_backup(name), lambda _: self.refresh_callback())

        self.run_async(self.git.meaningful_changed_files, after_dirty)

    def restore_with_backup(self, name):
        current_backup = self.manager.create_backup("before-restore-backup")
        result = self.manager.reset_to_backup(name)
        return tr("已恢复到 ") + name + tr("，恢复前状态已备份到 ") + f"{current_backup}: {result.stdout.strip()}"

    def delete_backup(self):
        name = self.selected_backup()
        if not name:
            return
        if QMessageBox.question(self, tr("确认删除"), f"{tr('删除备份')} {name}?") != QMessageBox.Yes:
            return
        self.run_async(lambda: self.manager.delete_backup(name), lambda _: self.load_backups())
