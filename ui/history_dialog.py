from PyQt5.QtCore import Qt, QThreadPool
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
    from core.git_worker import TaskWorker
    from ui.diff_view import DiffView
    from ui.help_widgets import make_help_box
except ModuleNotFoundError:
    from stm32_git_release_tool.core.i18n import tr
    from stm32_git_release_tool.core.git_worker import TaskWorker
    from stm32_git_release_tool.ui.diff_view import DiffView
    from stm32_git_release_tool.ui.help_widgets import make_help_box


class HistoryDialog(QDialog):
    def __init__(self, git_service, refresh_callback, reset_callback=None, verify_callback=None, parent=None):
        super().__init__(parent)
        self.git = git_service
        self.refresh_callback = refresh_callback
        self.reset_callback = reset_callback
        self.verify_callback = verify_callback
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle(tr("提交历史"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)

        self.history_list = QListWidget()
        self.history_list.setStyleSheet(
            """
            QListWidget {
                outline: 0;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                background: #ffffff;
                font-family: Consolas, "Cascadia Mono", monospace;
                font-size: 12px;
            }
            QListWidget::item {
                border: 0;
                padding: 4px 8px;
                min-height: 20px;
            }
            QListWidget::item:selected {
                background: #e8f0fe;
                color: #1d1d1f;
                border: 0;
            }
            QListWidget::item:hover {
                background: #f2f2f7;
            }
            """
        )
        self.diff_view = DiffView()
        self.view_diff_button = QPushButton(tr("查看代码 Diff"))
        self.revert_button = QPushButton(tr("安全回滚 Revert"))
        self.reset_button = QPushButton(tr("强制回退 Reset"))
        self.save_diff_button = QPushButton(tr("保存完整 Diff"))
        self.refresh_button = QPushButton(tr("刷新"))
        self.buttons = [
            self.view_diff_button,
            self.save_diff_button,
            self.revert_button,
            self.reset_button,
            self.refresh_button,
        ]

        button_layout = QHBoxLayout()
        for button in self.buttons:
            button_layout.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("提交历史说明", [
            "提交列表：按时间显示 commit hash、日期、tag 标记和提交说明。先选中一条提交，再执行下面的操作。",
            "查看代码 Diff 按钮：查看选中提交带来的源码/工程配置差异。左侧是变更文件，右侧是对应代码差异；绿色新增，红色删除，黄色为位置提示。",
            "保存完整 Diff 按钮：把选中提交的完整 patch 导出到 .stm32_git_tool/diff_reports/，用于备份、评审或问题追踪。",
            "安全回滚 Revert 按钮：生成一个新的撤销提交，不删除历史。适合已经发布或已经推送远程的提交。",
            "强制回退 Reset 按钮：把当前工程强制恢复到选中提交。属于危险操作，会检查未提交修改、要求保护密码和 RESET 确认，并自动创建 backup 分支。",
            "刷新按钮：重新加载提交历史。提交、回滚、回退后可点击刷新确认列表状态。",
            "推荐流程：先查看 Diff 确认内容；如果只是撤销某个提交，优先用 Revert；只有需要整体回到旧状态时才用 Reset。",
        ]))
        layout.addWidget(self.history_list, 2)
        layout.addLayout(button_layout)
        layout.addWidget(self.diff_view, 4)

        self.view_diff_button.clicked.connect(self.view_diff)
        self.save_diff_button.clicked.connect(self.save_diff)
        self.revert_button.clicked.connect(self.revert_commit)
        self.reset_button.clicked.connect(self.reset_commit)
        self.refresh_button.clicked.connect(self.load_history)
        self.load_history()

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

    def load_history(self):
        def apply(output):
            self.history_list.clear()
            self.history_list.addItems([line for line in output.splitlines() if line.strip()])
            if self.history_list.count() > 0:
                self.history_list.setCurrentRow(0)

        self.run_async(self.git.commit_history, on_finished=apply, refresh=False)

    def selected_hash(self):
        item = self.history_list.currentItem()
        if not item:
            return ""
        return item.text().split("\t", 1)[0].strip()

    def view_diff(self):
        commit_hash = self.selected_hash()
        if not commit_hash:
            QMessageBox.information(self, tr("未选择提交"), tr("请先在上方提交历史列表中选择一条记录。"))
            return
        self.diff_view.set_loading(tr("正在加载代码差异..."))
        self.run_async(lambda: self.git.code_diff_preview(commit_hash), on_finished=self.diff_view.set_diff, refresh=False)

    def save_diff(self):
        commit_hash = self.selected_hash()
        if not commit_hash:
            QMessageBox.information(self, tr("未选择提交"), tr("请先在上方提交历史列表中选择一条记录。"))
            return

        def apply(path):
            self.diff_view.set_plain(tr("完整 Diff 已保存到：\n{path}", path=path))

        self.run_async(lambda: self.git.save_diff(commit_hash), on_finished=apply, refresh=False)

    def revert_commit(self):
        commit_hash = self.selected_hash()
        if not commit_hash:
            QMessageBox.information(self, tr("未选择提交"), tr("请先在上方提交历史列表中选择一条记录。"))
            return
        if QMessageBox.question(self, tr("确认回滚"), tr("确认使用 git revert 撤销 {commit_hash}？", commit_hash=commit_hash)) != QMessageBox.Yes:
            return
        self.run_async(lambda: self.git.revert_commit(commit_hash), on_finished=lambda _: self.load_history())

    def reset_commit(self):
        commit_hash = self.selected_hash()
        if not commit_hash:
            QMessageBox.information(self, tr("未选择提交"), tr("请先在上方提交历史列表中选择一条记录。"))
            return
        if QMessageBox.question(
            self,
            tr("危险操作"),
            tr("确认强制回退到提交 {commit_hash}？\n\n工具会先创建 backup 分支，回退错误时可从“备份管理”恢复。", commit_hash=commit_hash),
        ) != QMessageBox.Yes:
            return
        if self.verify_callback and not self.verify_callback(tr("强制回退到 commit")):
            return

        def after_dirty(changes):
            if changes:
                QMessageBox.warning(self, tr("存在未提交修改"), tr("请先提交、暂存或放弃当前修改后再强制回退。"))
                return
            action = self.reset_callback or self.git.reset_hard_commit
            self.run_async(lambda: action(commit_hash), on_finished=lambda _: self.load_history())

        self.run_async(self.git.meaningful_changed_files, on_finished=after_dirty, refresh=False)
