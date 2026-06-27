from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

try:
    from core.i18n import tr
    from core.git_worker import TaskWorker
    from ui.help_widgets import make_help_box
except ModuleNotFoundError:
    from stm32_git_release_tool.core.i18n import tr
    from stm32_git_release_tool.core.git_worker import TaskWorker
    from stm32_git_release_tool.ui.help_widgets import make_help_box


class BranchDialog(QDialog):
    def __init__(self, git_service, refresh_callback, parent=None):
        super().__init__(parent)
        self.git = git_service
        self.refresh_callback = refresh_callback
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle(tr("分支管理"))
        self.resize(620, 380)

        self.branch_list = QListWidget()
        self.create_button = QPushButton(tr("创建分支"))
        self.checkout_button = QPushButton(tr("切换分支"))
        self.delete_button = QPushButton(tr("删除分支"))
        self.force_delete_button = QPushButton(tr("强制删除"))
        self.merge_button = QPushButton(tr("合并分支"))
        self.refresh_button = QPushButton(tr("刷新"))
        self.buttons = [
            self.create_button,
            self.checkout_button,
            self.delete_button,
            self.force_delete_button,
            self.merge_button,
            self.refresh_button,
        ]

        button_layout = QHBoxLayout()
        for button in self.buttons:
            button_layout.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("分支管理说明", [
            "分支列表：显示当前仓库的本地分支。先选中一个分支，再执行切换、删除或合并。",
            "创建分支按钮：从当前 HEAD 创建新分支。适合开发新功能或临时实验，建议命名为 feature/xxx、fix/xxx。",
            "切换分支按钮：切换到选中的分支。若当前有未提交工程修改，工具会先提示确认。",
            "删除分支按钮：执行普通删除，Git 会阻止删除未合并分支，适合日常清理。",
            "强制删除按钮：执行强制删除，即使分支未合并也会删除引用。确认该分支不再需要时才使用。",
            "合并分支按钮：把选中分支合并到当前分支。合并前确认自己当前在哪个分支；如果产生冲突，需要人工处理冲突后再提交。",
            "刷新按钮：重新读取当前仓库分支列表，用于切换、创建、删除后更新显示。",
        ]))
        layout.addWidget(self.branch_list)
        layout.addLayout(button_layout)

        self.create_button.clicked.connect(self.create_branch)
        self.checkout_button.clicked.connect(self.checkout_branch)
        self.delete_button.clicked.connect(lambda: self.delete_branch(False))
        self.force_delete_button.clicked.connect(lambda: self.delete_branch(True))
        self.merge_button.clicked.connect(self.merge_branch)
        self.refresh_button.clicked.connect(self.load_branches)
        self.load_branches()

    def run_async(self, func, on_finished=None, refresh=True):
        worker = TaskWorker(func)
        self.set_busy(True)
        worker.signals.error.connect(lambda text: QMessageBox.warning(self, tr("错误"), text))
        worker.signals.error.connect(lambda _: self.set_busy(False))
        worker.signals.finished.connect(lambda result: self.set_busy(False))
        if on_finished:
            worker.signals.finished.connect(on_finished)
        if refresh:
            worker.signals.finished.connect(lambda _: self.refresh_callback())
        self.thread_pool.start(worker)

    def set_busy(self, busy):
        for button in self.buttons:
            button.setEnabled(not busy)

    def load_branches(self):
        def apply(branches):
            self.branch_list.clear()
            self.branch_list.addItems(branches)

        self.run_async(self.git.list_branches, on_finished=apply, refresh=False)

    def selected_branch(self):
        item = self.branch_list.currentItem()
        return item.text() if item else ""

    def create_branch(self):
        name, ok = QInputDialog.getText(self, tr("创建分支"), tr("分支名称："))
        if ok and name.strip():
            self.run_async(lambda: self.git.create_branch(name.strip()), on_finished=lambda _: self.load_branches())

    def checkout_branch(self):
        branch = self.selected_branch()
        if not branch:
            return

        def after_dirty(changes):
            if changes:
                reply = QMessageBox.question(self, tr("存在未提交修改"), tr("当前存在未提交修改，仍要切换分支吗？"))
                if reply != QMessageBox.Yes:
                    return
            self.run_async(lambda: self.git.checkout_branch(branch), on_finished=lambda _: self.accept())

        self.run_async(self.git.meaningful_changed_files, on_finished=after_dirty, refresh=False)

    def delete_branch(self, force):
        branch = self.selected_branch()
        if not branch:
            return
        text = f"{tr('强制删除') if force else tr('删除分支')} {branch}?"
        if QMessageBox.question(self, tr("确认删除"), text) != QMessageBox.Yes:
            return
        self.run_async(lambda: self.git.delete_branch(branch, force=force), on_finished=lambda _: self.load_branches())

    def merge_branch(self):
        branch = self.selected_branch()
        if not branch:
            return
        if QMessageBox.question(self, tr("确认合并"), f"{tr('合并分支')} {branch}?") != QMessageBox.Yes:
            return
        self.run_async(lambda: self.git.merge_branch(branch), on_finished=lambda _: self.load_branches())
