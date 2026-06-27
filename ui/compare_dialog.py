from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

try:
    from core.git_worker import TaskWorker
    from ui.diff_view import DiffView
    from ui.help_widgets import make_help_box
except ModuleNotFoundError:
    from stm32_git_release_tool.core.git_worker import TaskWorker
    from stm32_git_release_tool.ui.diff_view import DiffView
    from stm32_git_release_tool.ui.help_widgets import make_help_box


class CompareDialog(QDialog):
    def __init__(self, git_service, parent=None):
        super().__init__(parent)
        self.git = git_service
        self.thread_pool = QThreadPool.globalInstance()
        self.setWindowTitle("版本差异对比")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)

        self.base_combo = QComboBox()
        self.target_combo = QComboBox()
        self.refresh_button = QPushButton("刷新版本")
        self.stat_button = QPushButton("文件变更统计")
        self.commits_button = QPushButton("提交差异")
        self.diff_button = QPushButton("代码 Diff")
        self.save_diff_button = QPushButton("保存完整 Diff")
        self.swap_button = QPushButton("交换")
        self.output = DiffView()
        self.direction_label = QLabel()
        self.direction_label.setStyleSheet("color:#6e6e73; padding:2px 0; font-weight:600;")

        form = QFormLayout()
        form.addRow("基准版本", self.base_combo)
        form.addRow("目标版本", self.target_combo)

        row = QHBoxLayout()
        for button in [
            self.refresh_button,
            self.swap_button,
            self.stat_button,
            self.commits_button,
            self.diff_button,
            self.save_diff_button,
        ]:
            row.addWidget(button)
        row.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("版本对比说明", [
            "基准版本下拉框：选择旧版本，可以是某个 tag，也可以是 HEAD。",
            "目标版本下拉框：选择新版本。对比结果表示从基准版本到目标版本发生的变化。",
            "刷新版本按钮：重新读取 tag 列表。新增 tag 或切换工程后使用。",
            "交换按钮：交换基准版本和目标版本，方便反向查看差异。",
            "文件变更统计按钮：显示变更文件列表和每个文件的增删行统计，适合先判断影响范围。",
            "提交差异按钮：显示两个版本之间包含哪些 commit，适合整理版本说明。",
            "代码 Diff 按钮：按文件展示源码和工程配置差异，过滤 bin、hex、map、o 等固件和编译产物。",
            "保存完整 Diff 按钮：导出完整 patch 到 .stm32_git_tool/diff_reports/，适合留档或交给别人审查。",
            "推荐流程：先看文件变更统计，再看提交差异，最后查看代码 Diff。",
        ]))
        layout.addLayout(form)
        layout.addWidget(self.direction_label)
        layout.addLayout(row)
        layout.addWidget(self.output)

        self.buttons = [
            self.refresh_button,
            self.stat_button,
            self.commits_button,
            self.diff_button,
            self.save_diff_button,
            self.swap_button,
        ]
        self.refresh_button.clicked.connect(self.load_versions)
        self.swap_button.clicked.connect(self.swap_versions)
        self.stat_button.clicked.connect(self.show_stat)
        self.commits_button.clicked.connect(self.show_commits)
        self.diff_button.clicked.connect(self.show_diff)
        self.save_diff_button.clicked.connect(self.save_diff)
        self.base_combo.currentIndexChanged.connect(self.update_direction_label)
        self.target_combo.currentIndexChanged.connect(self.update_direction_label)
        self.load_versions()

    def update_direction_label(self):
        base = self.base_combo.currentText().strip() or "-"
        target = self.target_combo.currentText().strip() or "-"
        self.direction_label.setText(
            f"当前对比方向：{base} -> {target}。红色表示 {base} 中存在但 {target} 中没有；绿色表示 {target} 新增。"
        )

    def set_busy(self, busy):
        for button in self.buttons:
            button.setEnabled(not busy)

    def run_async(self, func, on_finished=None):
        worker = TaskWorker(func)
        self.set_busy(True)
        worker.signals.error.connect(lambda text: QMessageBox.warning(self, "错误", text))
        worker.signals.error.connect(lambda _: self.set_busy(False))
        worker.signals.finished.connect(lambda result: self.set_busy(False))
        if on_finished:
            worker.signals.finished.connect(on_finished)
        self.thread_pool.start(worker)

    def load_versions(self):
        def apply(tags):
            self.base_combo.clear()
            self.target_combo.clear()
            refs = tags[:]
            if "HEAD" not in refs:
                refs.insert(0, "HEAD")
            self.base_combo.addItems(refs)
            self.target_combo.addItems(refs)
            if len(refs) > 1:
                self.base_combo.setCurrentIndex(1)
                self.target_combo.setCurrentIndex(0)
                self.update_direction_label()
            else:
                self.output.set_plain("当前没有可对比的 tag。请先提交并发布至少一个版本，或使用 HEAD 与已有 tag 对比。")

        self.run_async(self.git.list_tags, on_finished=apply)

    def selected_refs(self):
        base = self.base_combo.currentText().strip()
        target = self.target_combo.currentText().strip()
        if not base or not target:
            QMessageBox.information(self, "版本不足", "请至少选择两个版本或 HEAD。")
            self.output.set_plain("请选择基准版本和目标版本。")
            return "", ""
        if base == target:
            QMessageBox.information(self, "版本相同", "基准版本和目标版本相同，没有可对比内容。")
            self.output.set_plain("基准版本和目标版本相同，没有可对比内容。")
            return "", ""
        return base, target

    def swap_versions(self):
        base_index = self.base_combo.currentIndex()
        target_index = self.target_combo.currentIndex()
        self.base_combo.setCurrentIndex(target_index)
        self.target_combo.setCurrentIndex(base_index)
        self.update_direction_label()

    def show_stat(self):
        base, target = self.selected_refs()
        if not base:
            return
        self.output.set_plain("正在生成文件变更统计...")
        self.run_async(
            lambda: self.git.diff_stat_between(base, target),
            on_finished=lambda text: self.output.set_plain(text or "没有文件差异。"),
        )

    def show_commits(self):
        base, target = self.selected_refs()
        if not base:
            return
        self.output.set_plain("正在查询提交差异...")
        self.run_async(
            lambda: self.git.commits_between(base, target),
            on_finished=lambda text: self.output.set_plain(text or "没有新增提交。"),
        )

    def show_diff(self):
        base, target = self.selected_refs()
        if not base:
            return
        self.output.set_loading("正在生成代码差异，固件/编译产物会被过滤...")
        self.run_async(
            lambda: self.git.code_diff_between_preview(base, target),
            on_finished=lambda text: self.output.set_diff(text or "没有代码差异。"),
        )

    def save_diff(self):
        base, target = self.selected_refs()
        if not base:
            return
        self.output.set_plain("正在保存完整 diff...")
        self.run_async(
            lambda: self.git.save_diff_between(base, target),
            on_finished=lambda path: self.output.set_plain(f"完整 Diff 已保存到：\n{path}"),
        )
