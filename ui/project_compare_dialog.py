import os
from datetime import datetime

from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

try:
    from core.directory_compare import DirectoryComparer
    from core.git_worker import TaskWorker
    from core.i18n import tr
    from ui.diff_view import DiffView
    from ui.help_widgets import make_help_box
except ModuleNotFoundError:
    from stm32_git_release_tool.core.directory_compare import DirectoryComparer
    from stm32_git_release_tool.core.git_worker import TaskWorker
    from stm32_git_release_tool.core.i18n import tr
    from stm32_git_release_tool.ui.diff_view import DiffView
    from stm32_git_release_tool.ui.help_widgets import make_help_box


class ProjectCompareDialog(QDialog):
    def __init__(self, current_project, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.thread_pool = QThreadPool.globalInstance()
        self.comparer = None
        self.result = None
        self.filtered_result = None
        self.active_worker = None
        self.setWindowTitle(tr("工程目录对比"))
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.resize(1280, 760)
        self.setMinimumSize(980, 620)

        self.base_input = QLineEdit(os.path.realpath(current_project))
        self.target_input = QLineEdit()
        self.base_button = QPushButton(tr("选择旧工程"))
        self.target_button = QPushButton(tr("选择新工程"))
        self.swap_button = QPushButton(tr("交换"))
        self.compare_button = QPushButton(tr("开始对比"))
        self.compare_button.setObjectName("PrimaryButton")
        self.export_button = QPushButton(tr("导出筛选结果"))
        self.export_button.setEnabled(False)
        self.export_all_button = QPushButton(tr("导出完整报告"))
        self.export_all_button.setEnabled(False)
        self.status_filter = QComboBox()
        self.status_filter.addItem(tr("全部变更"), "all")
        self.status_filter.addItem(tr("新增文件"), "added")
        self.status_filter.addItem(tr("删除文件"), "removed")
        self.status_filter.addItem(tr("修改文件"), "modified")
        self.status_filter.addItem(tr("改名文件"), "renamed")
        self.file_type_filter = QComboBox()
        self.file_type_filter.addItem(tr("全部文件类型"), "all")
        self.file_type_filter.addItem(tr("源代码"), "source")
        self.file_type_filter.addItem(tr("头文件"), "header")
        self.file_type_filter.addItem(tr("工程配置"), "project")
        self.file_type_filter.addItem(tr("文本和文档"), "document")
        self.file_type_filter.addItem(tr("固件和二进制"), "binary")
        self.file_type_filter.addItem(tr("其他文件"), "other")
        self.filename_filter = QLineEdit()
        self.filename_filter.setClearButtonEnabled(True)
        self.filename_filter.setPlaceholderText(tr("输入文件名或路径"))
        self.extension_filter = QLineEdit()
        self.extension_filter.setClearButtonEnabled(True)
        self.extension_filter.setPlaceholderText(tr("例如 .c,.h"))
        self.exclude_input = QLineEdit()
        self.exclude_input.setClearButtonEnabled(True)
        self.exclude_input.setPlaceholderText(tr("例如 Middlewares,*.log"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.cancel_button = QPushButton(tr("取消"))
        self.cancel_button.setEnabled(False)
        self.summary_label = QLabel(tr("请选择两个工程并开始对比。"))
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("color:#424245; padding:3px 0; font-weight:600;")
        self.output = DiffView()

        base_row = QHBoxLayout()
        base_row.addWidget(self.base_input, 1)
        base_row.addWidget(self.base_button)
        target_row = QHBoxLayout()
        target_row.addWidget(self.target_input, 1)
        target_row.addWidget(self.target_button)

        form = QFormLayout()
        form.addRow(tr("旧工程"), base_row)
        form.addRow(tr("新工程"), target_row)

        actions = QHBoxLayout()
        actions.addWidget(self.swap_button)
        actions.addWidget(self.compare_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.export_all_button)
        actions.addStretch()

        filters = QHBoxLayout()
        filters.addWidget(QLabel(tr("变更类型")))
        filters.addWidget(self.status_filter)
        filters.addWidget(QLabel(tr("文件类型")))
        filters.addWidget(self.file_type_filter)
        filters.addWidget(QLabel(tr("文件搜索")))
        filters.addWidget(self.filename_filter, 1)
        filters.addStretch()

        options = QHBoxLayout()
        options.addWidget(QLabel(tr("扩展名筛选")))
        options.addWidget(self.extension_filter)
        options.addWidget(QLabel(tr("本次临时排除")))
        options.addWidget(self.exclude_input, 1)

        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_bar, 1)
        progress_row.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("工程对比说明", [
            "旧工程和新工程可以是任意两个目录，不要求存在 Git 仓库。对比结果表示从旧工程到新工程发生的变化。",
            "默认忽略 .git、.stm32_git_tool、Debug、Objects、Listings、build 和设置中的排除规则。",
            "文本源码按行显示 Diff；bin、hex 等二进制文件只比较大小和 SHA-256。",
            "完成一次扫描后，可以按变更类型和文件类型筛选，不会重复扫描工程。",
            "文件搜索和扩展名筛选只改变显示；本次临时排除规则会在下一次扫描时生效。",
            "扫描、哈希和差异生成过程中会显示进度，可以随时安全取消。",
            "对比过程只读取两个工程，不会修改、删除或复制工程文件。",
        ]))
        layout.addLayout(form)
        layout.addLayout(actions)
        layout.addLayout(filters)
        layout.addLayout(options)
        layout.addLayout(progress_row)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.output, 1)

        self.buttons = [
            self.base_button,
            self.target_button,
            self.swap_button,
            self.compare_button,
            self.export_button,
            self.export_all_button,
            self.status_filter,
            self.file_type_filter,
            self.filename_filter,
            self.extension_filter,
            self.exclude_input,
        ]
        self.base_button.clicked.connect(lambda: self.select_directory(self.base_input))
        self.target_button.clicked.connect(lambda: self.select_directory(self.target_input))
        self.swap_button.clicked.connect(self.swap_directories)
        self.compare_button.clicked.connect(self.compare_directories)
        self.export_button.clicked.connect(lambda: self.export_report(filtered=True))
        self.export_all_button.clicked.connect(lambda: self.export_report(filtered=False))
        self.status_filter.currentIndexChanged.connect(self.apply_filters)
        self.file_type_filter.currentIndexChanged.connect(self.apply_filters)
        self.filename_filter.textChanged.connect(self.apply_filters)
        self.extension_filter.textChanged.connect(self.apply_filters)
        self.cancel_button.clicked.connect(self.cancel_current_operation)

    def set_busy(self, busy):
        for button in self.buttons:
            button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy and self.active_worker is not None and self.active_worker.controlled)
        if not busy:
            self.export_button.setEnabled(self.result is not None)
            self.export_all_button.setEnabled(self.result is not None)
            self.cancel_button.setEnabled(False)

    def run_async(self, func, on_finished=None, controlled=False):
        worker = TaskWorker(func, controlled=controlled)
        self.active_worker = worker
        self.set_busy(True)
        worker.signals.error.connect(lambda text: QMessageBox.warning(self, tr("错误"), text))
        worker.signals.error.connect(lambda _: self.worker_done())
        worker.signals.finished.connect(lambda _: self.worker_done())
        worker.signals.cancelled.connect(self.operation_cancelled)
        worker.signals.progress.connect(self.update_progress)
        if on_finished:
            worker.signals.finished.connect(on_finished)
        self.thread_pool.start(worker)

    def worker_done(self):
        self.active_worker = None
        self.set_busy(False)

    def update_progress(self, percent, message):
        percent = max(0, min(100, percent))
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{message}  %p%")

    def cancel_current_operation(self):
        if self.active_worker and self.active_worker.controlled:
            self.cancel_button.setEnabled(False)
            self.active_worker.cancel()
            self.progress_bar.setFormat(tr("正在取消..."))

    def operation_cancelled(self):
        self.active_worker = None
        self.set_busy(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(tr("操作已取消"))
        self.summary_label.setText(tr("工程对比已取消，没有修改任何工程文件。"))
        self.output.set_plain(tr("操作已取消。"))

    def select_directory(self, target_input):
        current = target_input.text().strip() or self.base_input.text().strip() or os.getcwd()
        path = QFileDialog.getExistingDirectory(self, tr("选择工程目录"), current)
        if path:
            target_input.setText(os.path.realpath(path))
            self.clear_result()

    def swap_directories(self):
        base = self.base_input.text()
        self.base_input.setText(self.target_input.text())
        self.target_input.setText(base)
        self.clear_result()
        self.summary_label.setText(tr("请选择两个工程并开始对比。"))
        self.output.set_plain(tr("请选择两个工程并开始对比。"))

    def clear_result(self):
        self.comparer = None
        self.result = None
        self.filtered_result = None
        self.export_button.setEnabled(False)
        self.export_all_button.setEnabled(False)
        self.summary_label.setText(tr("请选择两个工程并开始对比。"))
        self.output.set_plain(tr("请选择两个工程并开始对比。"))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat(tr("等待开始"))

    def compare_directories(self):
        base_dir = self.base_input.text().strip()
        target_dir = self.target_input.text().strip()
        if not base_dir or not target_dir:
            QMessageBox.information(self, tr("缺少工程目录"), tr("请选择旧工程和新工程。"))
            return

        self.clear_result()
        self.output.set_loading(tr("正在扫描并比较两个工程..."))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(1)
        self.progress_bar.setFormat(f"{tr('正在扫描...')}  %p%")
        temporary_excludes = self._split_values(self.exclude_input.text())

        def task(cancel_token, progress_callback):
            compare_config = dict(self.config)
            compare_config["exclude_dirs"] = list(self.config.get("exclude_dirs", []))
            compare_config["exclude_patterns"] = list(self.config.get("exclude_patterns", []))
            for rule in temporary_excludes:
                if any(char in rule for char in "*?[]"):
                    compare_config["exclude_patterns"].append(rule)
                else:
                    compare_config["exclude_dirs"].append(rule)
            comparer = DirectoryComparer(base_dir, target_dir, compare_config)
            result = comparer.compare(cancel_token, progress_callback)
            comparer.prepare_diffs(result, cancel_token, progress_callback)
            return comparer, result

        def apply(data):
            self.comparer, self.result = data
            self.export_button.setEnabled(True)
            self.export_all_button.setEnabled(True)
            self.apply_filters()

        self.run_async(task, on_finished=apply, controlled=True)

    def apply_filters(self):
        if not self.comparer or not self.result:
            return
        self.filtered_result = self.comparer.filter_result(
            self.result,
            str(self.status_filter.currentData()),
            str(self.file_type_filter.currentData()),
            self.filename_filter.text(),
            self._split_values(self.extension_filter.text()),
        )
        filtered_count = self._difference_count(self.filtered_result)
        total_count = self._difference_count(self.result)
        self.summary_label.setText(tr(
            "当前筛选：新增 {added}  删除 {removed}  修改 {modified}  改名 {renamed}  |  全部差异 {total}  相同 {same}",
            added=len(self.filtered_result["added"]),
            removed=len(self.filtered_result["removed"]),
            modified=len(self.filtered_result["modified"]),
            renamed=len(self.filtered_result.get("renamed", [])),
            total=total_count,
            same=self.result["same_count"],
        ))
        if filtered_count == 0 and not self.filtered_result["errors"]:
            self.output.set_plain(tr("当前筛选条件下没有文件差异。"))
            return
        preview = self.comparer.build_diff(self.filtered_result, max_chars=200000)
        self.output.set_diff(preview)

    @staticmethod
    def _difference_count(result):
        return (
            len(result["added"])
            + len(result["removed"])
            + len(result["modified"])
            + len(result.get("renamed", []))
        )

    @staticmethod
    def _split_values(text):
        return [item.strip() for item in text.replace("；", ",").replace(";", ",").split(",") if item.strip()]

    def export_report(self, filtered):
        if not self.comparer or not self.result:
            QMessageBox.information(self, tr("没有对比结果"), tr("请先完成一次工程对比。"))
            return
        export_result = self.filtered_result if filtered and self.filtered_result else self.result
        suffix = "filtered" if filtered else "full"
        default_name = f"project_diff_{suffix}_{datetime.now():%Y%m%d-%H%M%S}.txt"
        initial_path = os.path.join(os.path.dirname(self.base_input.text().strip()), default_name)
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("导出差异报告"),
            initial_path,
            tr("文本文件 (*.txt);;所有文件 (*)"),
        )
        if not path:
            return

        def done(saved_path):
            QMessageBox.information(self, tr("导出完成"), tr("差异报告已保存到：\n{path}", path=saved_path))

        self.run_async(lambda: self.comparer.save_report(export_result, path), on_finished=done)

    def closeEvent(self, event):
        if self.active_worker and self.active_worker.controlled:
            self.active_worker.cancel()
        super().closeEvent(event)
