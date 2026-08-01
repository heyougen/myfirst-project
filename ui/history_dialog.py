from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
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
        self.busy = False
        self.history_refs = []
        self.setWindowTitle(tr("提交历史"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)

        self.history_list = QListWidget()
        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(tr("搜索版本号、日期或修改说明"))
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
        self.delete_tag_button = QPushButton(tr("删除 Tag"))
        self.delete_commit_button = QPushButton(tr("删除最新 Commit"))
        self.save_diff_button = QPushButton(tr("保存完整 Diff"))
        self.refresh_button = QPushButton(tr("刷新"))
        self.buttons = [
            self.view_diff_button,
            self.save_diff_button,
            self.revert_button,
            self.reset_button,
            self.delete_tag_button,
            self.delete_commit_button,
            self.refresh_button,
        ]

        button_layout = QGridLayout()
        for index, button in enumerate(self.buttons):
            button_layout.addWidget(button, index // 4, index % 4)

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("提交历史说明", [
            "版本列表：使用与“选择版本点”相同的格式显示 tag、commit、分钟时间和修改说明。先选中一条记录，再执行下面的操作。",
            "搜索框：可以按版本号、日期或修改说明实时筛选历史记录。",
            "查看代码 Diff 按钮：查看选中提交带来的源码/工程配置差异。左侧是变更文件，右侧是对应代码差异；绿色新增，红色删除，黄色为位置提示。",
            "保存完整 Diff 按钮：把选中提交的完整 patch 导出到 .stm32_git_tool/diff_reports/，用于备份、评审或问题追踪。",
            "安全回滚 Revert 按钮：生成一个新的撤销提交，不删除历史。适合已经发布或已经推送远程的提交。",
            "强制回退 Reset 按钮：把当前工程强制恢复到选中提交。属于危险操作，会检查未提交修改、要求保护密码和 RESET 确认，并自动创建 backup 分支。",
            "删除 Tag 按钮：只删除选中的本地 tag，不删除代码和 commit，也不会删除远程 tag。需要两次确认。",
            "删除最新 Commit 按钮：只允许删除当前分支顶部、未打 tag、未出现在本地远程跟踪分支中的 commit。删除前自动备份并需要两次确认。",
            "刷新按钮：重新加载提交历史。提交、回滚、回退后可点击刷新确认列表状态。",
            "推荐流程：先查看 Diff 确认内容；如果只是撤销某个提交，优先用 Revert；只有需要整体回到旧状态时才用 Reset。",
        ]))
        layout.addWidget(self.search_input)
        layout.addWidget(self.history_list, 2)
        layout.addLayout(button_layout)
        layout.addWidget(self.diff_view, 4)

        self.view_diff_button.clicked.connect(self.view_diff)
        self.save_diff_button.clicked.connect(self.save_diff)
        self.revert_button.clicked.connect(self.revert_commit)
        self.reset_button.clicked.connect(self.reset_commit)
        self.delete_tag_button.clicked.connect(self.delete_tag)
        self.delete_commit_button.clicked.connect(self.delete_latest_commit)
        self.refresh_button.clicked.connect(self.load_history)
        self.history_list.currentItemChanged.connect(self.update_delete_buttons)
        self.search_input.textChanged.connect(self.apply_history_filter)
        self.update_delete_buttons()
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
        self.busy = busy
        for button in self.buttons:
            button.setEnabled(not busy)
        if not busy:
            self.update_delete_buttons()

    def load_history(self):
        def apply(refs):
            self.history_refs = [ref for ref in refs if ref["kind"] != "head"]
            self.apply_history_filter()

        self.run_async(self.git.list_compare_refs, on_finished=apply, refresh=False)

    def apply_history_filter(self):
        selected_ref = self.selected_hash()
        keyword = self.search_input.text().strip().casefold()
        self.history_list.clear()
        selected_row = -1
        for ref in self.history_refs:
            if keyword and keyword not in ref["label"].casefold():
                continue
            item = QListWidgetItem(ref["label"])
            item.setData(Qt.UserRole, ref["ref"])
            item.setData(Qt.UserRole + 1, ref["kind"])
            self.history_list.addItem(item)
            if selected_ref and str(ref["ref"]) == selected_ref:
                selected_row = self.history_list.count() - 1
        if selected_row >= 0:
            self.history_list.setCurrentRow(selected_row)
        elif self.history_list.count() > 0:
            self.history_list.setCurrentRow(0)

    def selected_hash(self):
        item = self.history_list.currentItem()
        if not item:
            return ""
        ref = item.data(Qt.UserRole)
        return str(ref).strip() if ref else ""

    def selected_kind(self):
        item = self.history_list.currentItem()
        if not item:
            return ""
        kind = item.data(Qt.UserRole + 1)
        return str(kind).strip() if kind else ""

    def update_delete_buttons(self):
        kind = self.selected_kind()
        self.delete_tag_button.setEnabled(not self.busy and kind == "tag")
        self.delete_commit_button.setEnabled(not self.busy and kind == "commit")

    @staticmethod
    def _typed_confirmation(parent, title, prompt, expected):
        token, ok = QInputDialog.getText(parent, tr(title), tr(prompt))
        return ok and token.strip() == expected

    def delete_tag(self):
        tag = self.selected_hash()
        if not tag or self.selected_kind() != "tag":
            QMessageBox.information(self, tr("未选择 Tag"), tr("请先选择一条 tag 记录。"))
            return
        if QMessageBox.question(
            self,
            tr("确认删除 Tag"),
            tr("确认删除本地 tag {tag}？\n\n代码和 commit 会保留，远程 tag 不会被删除。", tag=tag),
        ) != QMessageBox.Yes:
            return
        if not self._typed_confirmation(
            self,
            "二次确认",
            "请输入 DELETE TAG 确认删除：",
            "DELETE TAG",
        ):
            QMessageBox.information(self, tr("已取消"), tr("确认文字不正确，操作已取消。"))
            return
        self.run_async(lambda: self.git.delete_tag(tag), on_finished=lambda _: self.load_history())

    def delete_latest_commit(self):
        selected_ref = self.selected_hash()
        if not selected_ref or self.selected_kind() != "commit":
            QMessageBox.information(self, tr("未选择 Commit"), tr("请先选择一条 commit 记录。"))
            return

        def inspect():
            return {
                "branch": self.git.current_branch(),
                "head": self.git.resolve_commit("HEAD"),
                "selected": self.git.resolve_commit(selected_ref),
                "tag": self.git.current_tag(),
                "remote_branches": self.git.remote_branches_containing(selected_ref),
                "has_parent": self.git.commit_has_parent(selected_ref),
                "changes": self.git.meaningful_changed_files(),
            }

        def confirm_delete(info):
            if info["branch"] == "(detached)":
                QMessageBox.warning(self, tr("不能删除 Commit"), tr("当前处于历史查看模式，请先返回正常分支。"))
                return
            if info["selected"] != info["head"]:
                QMessageBox.warning(self, tr("不能删除 Commit"), tr("只能删除当前分支最顶部的 commit。"))
                return
            if info["tag"]:
                QMessageBox.warning(self, tr("不能删除 Commit"), tr("当前 commit 已有 tag，请先删除 tag，或使用 Revert。"))
                return
            if info["remote_branches"]:
                branches = "\n".join(info["remote_branches"])
                QMessageBox.warning(
                    self,
                    tr("不能删除 Commit"),
                    tr("当前 commit 已存在于远程跟踪分支中，不能按未发布 commit 删除：\n{branches}\n\n请使用 Revert。", branches=branches),
                )
                return
            if not info["has_parent"]:
                QMessageBox.warning(self, tr("不能删除 Commit"), tr("初始 commit 没有上一个版本，不能删除。"))
                return
            if info["changes"]:
                QMessageBox.warning(self, tr("存在未提交修改"), tr("请先提交、暂存或放弃当前修改后再删除 commit。"))
                return
            if QMessageBox.question(
                self,
                tr("确认删除最新 Commit"),
                tr("确认删除当前最新 commit？\n\n工具会先创建 backup 分支，之后可从备份管理恢复。"),
            ) != QMessageBox.Yes:
                return
            if not self._typed_confirmation(
                self,
                "二次确认",
                "请输入 DELETE COMMIT 确认删除：",
                "DELETE COMMIT",
            ):
                QMessageBox.information(self, tr("已取消"), tr("确认文字不正确，操作已取消。"))
                return
            action = self.reset_callback or self.git.reset_hard
            self.run_async(lambda: action("HEAD^"), on_finished=lambda _: self.load_history())

        self.run_async(inspect, on_finished=confirm_delete, refresh=False)

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
