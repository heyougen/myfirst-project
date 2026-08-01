import os
from datetime import datetime

from PyQt5.QtCore import QThreadPool, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QComboBox,
    QInputDialog,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from core.backup_manager import BackupManager
    from core.config_manager import AppStateManager, ConfigManager
    from core.git_service import GitService
    from core.git_worker import TaskWorker
    from core.i18n import LANGUAGE_OPTIONS, set_language, tr
    from core.diagnostics import Diagnostics
    from core.protection import ensure_writable_file, hash_password, protect_repository_dirs, protection_enabled, repository_dirs_hidden, show_repository_dirs, verify_password
    from core.project_cleaner import ProjectCleaner
    from core.project_scanner import ProjectScanner
    from core.recovery import Recovery
    from core.release_packager import ReleasePackager
    from core.repo_guard import RepoGuard
    from core.tool_paths import ensure_tool_dir, tool_file
    from core.versioning import is_valid_version, normalize_version, version_help
    from ui.backup_dialog import BackupDialog
    from ui.branch_dialog import BranchDialog
    from ui.compare_dialog import CompareDialog
    from ui.help_widgets import make_help_box
    from ui.history_dialog import HistoryDialog
    from ui.project_compare_dialog import ProjectCompareDialog
    from ui.settings_dialog import SettingsDialog
    from ui.version_ref_combo import VersionRefComboBox
except ModuleNotFoundError:
    from stm32_git_release_tool.core.backup_manager import BackupManager
    from stm32_git_release_tool.core.config_manager import AppStateManager, ConfigManager
    from stm32_git_release_tool.core.git_service import GitService
    from stm32_git_release_tool.core.git_worker import TaskWorker
    from stm32_git_release_tool.core.i18n import LANGUAGE_OPTIONS, set_language, tr
    from stm32_git_release_tool.core.diagnostics import Diagnostics
    from stm32_git_release_tool.core.protection import ensure_writable_file, hash_password, protect_repository_dirs, protection_enabled, repository_dirs_hidden, show_repository_dirs, verify_password
    from stm32_git_release_tool.core.project_cleaner import ProjectCleaner
    from stm32_git_release_tool.core.project_scanner import ProjectScanner
    from stm32_git_release_tool.core.recovery import Recovery
    from stm32_git_release_tool.core.release_packager import ReleasePackager
    from stm32_git_release_tool.core.repo_guard import RepoGuard
    from stm32_git_release_tool.core.tool_paths import ensure_tool_dir, tool_file
    from stm32_git_release_tool.core.versioning import is_valid_version, normalize_version, version_help
    from stm32_git_release_tool.ui.backup_dialog import BackupDialog
    from stm32_git_release_tool.ui.branch_dialog import BranchDialog
    from stm32_git_release_tool.ui.compare_dialog import CompareDialog
    from stm32_git_release_tool.ui.help_widgets import make_help_box
    from stm32_git_release_tool.ui.history_dialog import HistoryDialog
    from stm32_git_release_tool.ui.project_compare_dialog import ProjectCompareDialog
    from stm32_git_release_tool.ui.settings_dialog import SettingsDialog
    from stm32_git_release_tool.ui.version_ref_combo import VersionRefComboBox


STM32_GITIGNORE_LINES = [
    "Debug/",
    "Objects/",
    "Listings/",
    ".stm32_git_tool/",
    "*.uvguix.*",
    "*.uvguix",
    "*.uvgui.*",
    "*.uvgui",
    "*.build_log.htm",
    "*.htm",
    "*.map",
    "*.axf",
    "*.o",
    "*.d",
]


MAC_STYLE = """
QMainWindow, QWidget {
    background: #f5f5f7;
    color: #1d1d1f;
    font-family: "Microsoft YaHei", "Segoe UI", Arial;
    font-size: 13px;
}
QGroupBox {
    background: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 8px;
    margin-top: 6px;
    padding: 8px 8px 6px 8px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QLabel#TitleLabel {
    font-size: 20px;
    font-weight: 700;
}
QLabel#MutedLabel {
    color: #6e6e73;
}
QLabel#StatusPill {
    background: #eef4ff;
    color: #0057d9;
    border-radius: 10px;
    padding: 4px 10px;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 7px;
    padding: 4px 9px;
    min-height: 16px;
}
QPushButton:hover {
    background: #f2f2f7;
}
QPushButton:pressed {
    background: #e8e8ed;
}
QPushButton:disabled {
    color: #a1a1a6;
    background: #f2f2f7;
}
QPushButton#PrimaryButton {
    background: #0071e3;
    border-color: #0071e3;
    color: white;
    font-weight: 600;
}
QPushButton#DangerButton {
    background: #fff5f5;
    border-color: #ffb3b3;
    color: #b00020;
}
QLineEdit, QComboBox, QTextEdit, QListWidget {
    background: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 7px;
    padding: 4px;
}
QTextEdit {
    font-family: Consolas, "Cascadia Mono", monospace;
}
QTabWidget::pane {
    border: 0;
    margin: 0;
    padding: 0;
    background: transparent;
    top: -1px;
}
QTabWidget {
    border: 0;
    background: transparent;
}
QTabBar {
    border: 0;
    background: transparent;
}
QTabBar::base {
    border: 0;
    height: 0;
    background: transparent;
}
QTabBar::tab {
    background: #e8e8ed;
    border: 0;
    border-radius: 7px;
    padding: 4px 10px;
    margin: 2px;
}
QTabBar::tab:focus {
    outline: none;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #0071e3;
    font-weight: 600;
}
QFrame#Sidebar {
    background: #ffffff;
    border: 1px solid #e5e5ea;
    border-radius: 10px;
}
"""


class MainWindow(QMainWindow):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(object)
    busy_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("FST-GIT发布工具V1.2"))
        self.resize(1000, 580)
        self.setStyleSheet(MAC_STYLE)

        self.thread_pool = QThreadPool.globalInstance()
        self.busy_count = 0
        self.last_repo_text = tr("未检测")
        self.last_status = {
            "repo": False,
            "branch": "-",
            "tag": "-",
            "dirty": "-",
            "refs": [],
            "current_ref": "",
            "current_commit": "",
        }
        self.action_buttons = []

        self.app_state_manager = AppStateManager()
        self.app_state = self.app_state_manager.load()
        self.project_path = self._startup_project_path()
        ensure_tool_dir(self.project_path)
        self.config_manager = ConfigManager(tool_file(self.project_path, "app_config.json"))
        self.config = self.config_manager.load()
        set_language(self.config.get("language", "zh_CN"))
        self.setWindowTitle(tr("FST-GIT发布工具V1.2"))
        self.git = GitService(self.project_path, self.log)
        self.log_file_path = self._make_log_file_path()
        protect_repository_dirs(self.project_path, self.log)
        self.app_state_manager.save_last_project(self.project_path)

        self._build_ui()
        self.log_signal.connect(self._append_log)
        self.status_signal.connect(self._apply_status)
        self.busy_signal.connect(self._set_busy)
        self.refresh_status()

    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(260)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(10, 10, 10, 10)
        side.setSpacing(5)

        self.title_label = QLabel(tr("FST-GIT发布工具V1.2"))
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QLabel(tr("Git 版本管理 / 清理 / Release 打包"))
        self.subtitle_label.setObjectName("MutedLabel")

        self.repo_label = QLabel(tr("未检测"))
        self.repo_label.setObjectName("StatusPill")
        self.path_label = QLabel(self.project_path)
        self.path_label.setWordWrap(True)
        self.branch_label = QLabel("-")
        self.tag_label = QLabel("-")
        self.dirty_label = QLabel("-")

        self.select_path_button = QPushButton(tr("选择工程目录"))
        self.refresh_button = QPushButton(tr("刷新状态"))
        self.init_button = QPushButton(tr("初始化工程"))
        self.init_button.setObjectName("PrimaryButton")
        self.return_branch_button = QPushButton(tr("返回分支"))
        self.health_button = QPushButton(tr("检查工程"))
        self.diagnostics_button = QPushButton(tr("导出诊断包"))
        self.backup_button = QPushButton(tr("备份管理"))
        self.toggle_git_dirs_button = QPushButton(tr("显示 Git目录"))

        side.addWidget(self.title_label)
        side.addWidget(self.subtitle_label)
        side.addSpacing(4)
        side.addWidget(self.repo_label)
        self.path_title_label = QLabel(tr("工程路径"))
        side.addWidget(self.path_title_label)
        side.addWidget(self.path_label)
        self.branch_title_label = QLabel(tr("当前分支"))
        side.addWidget(self.branch_title_label)
        side.addWidget(self.branch_label)
        self.tag_title_label = QLabel(tr("当前 tag"))
        side.addWidget(self.tag_title_label)
        side.addWidget(self.tag_label)
        self.dirty_title_label = QLabel(tr("工作区状态"))
        side.addWidget(self.dirty_title_label)
        side.addWidget(self.dirty_label)
        side.addSpacing(6)
        side.addWidget(self.select_path_button)
        side.addWidget(self.refresh_button)
        side.addWidget(self.init_button)
        side.addWidget(self.return_branch_button)
        side.addWidget(self.health_button)
        side.addWidget(self.diagnostics_button)
        side.addWidget(self.backup_button)
        side.addWidget(self.toggle_git_dirs_button)
        side.addStretch()

        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(6)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.tabs.setMaximumHeight(270)
        self.tabs.addTab(self._build_version_tab(), tr("版本发布"))
        self.tabs.addTab(self._build_branch_tab(), tr("分支管理"))
        self.tabs.addTab(self._build_history_tab(), tr("历史记录"))
        self.tabs.addTab(self._build_compare_tab(), tr("版本对比"))
        self.tabs.addTab(self._build_project_compare_tab(), tr("工程对比"))
        self.tabs.addTab(self._build_clean_tab(), tr("工程清理"))
        self.tabs.addTab(self._build_remote_tab(), tr("远程同步"))
        self.tabs.addTab(self._build_settings_tab(), tr("设置"))
        self._build_language_switch()

        self.log_box = QGroupBox(tr("执行日志"))
        self.log_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        log_layout = QVBoxLayout(self.log_box)
        log_layout.setContentsMargins(6, 8, 6, 6)
        log_layout.setSpacing(4)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(230)
        self.log_text.setPlaceholderText(tr("Git 命令、清理、打包、错误输出都会显示在这里。"))
        self.clear_log_button = QPushButton(tr("清空日志"))
        log_layout.addWidget(self.log_text)
        log_layout.addWidget(self.clear_log_button)

        content.addWidget(self.tabs, 0)
        content.addWidget(self.log_box, 1)

        root.addWidget(sidebar)
        root.addLayout(content, 1)
        self.setCentralWidget(central)

        self.select_path_button.clicked.connect(self.select_project_path)
        self.refresh_button.clicked.connect(self.refresh_status)
        self.init_button.clicked.connect(self.init_project)
        self.return_branch_button.clicked.connect(self.return_to_branch)
        self.health_button.clicked.connect(self.run_health_check)
        self.diagnostics_button.clicked.connect(self.export_diagnostics)
        self.backup_button.clicked.connect(self.open_backup_dialog)
        self.toggle_git_dirs_button.clicked.connect(self.toggle_git_dirs_visibility)
        self.clear_log_button.clicked.connect(self.log_text.clear)

    def _card(self, title):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        return box, layout

    def _build_version_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)
        self.version_info_box = QGroupBox(tr("版本信息"))
        form = QFormLayout(self.version_info_box)
        form.setContentsMargins(6, 6, 6, 6)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(4)
        self.version_input = QLineEdit()
        self.version_input.setPlaceholderText(tr("例如 v1.2"))
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(tr("修改说明，例如 修复串口通信问题"))
        self.tag_combo = VersionRefComboBox()
        self.version_title_label = QLabel(tr("版本号"))
        self.desc_title_label = QLabel(tr("修改说明"))
        self.tag_select_title_label = QLabel(tr("选择版本点"))
        form.addRow(self.version_title_label, self.version_input)
        form.addRow(self.desc_title_label, self.desc_input)
        form.addRow(self.tag_select_title_label, self.tag_combo)

        self.version_actions_box = QGroupBox(tr("版本操作"))
        buttons = QGridLayout(self.version_actions_box)
        buttons.setContentsMargins(6, 6, 6, 6)
        buttons.setHorizontalSpacing(6)
        buttons.setVerticalSpacing(4)
        self.commit_button = QPushButton(tr("提交版本"))
        self.commit_button.setObjectName("PrimaryButton")
        self.release_button = QPushButton(tr("发布 Release"))
        self.release_button.setObjectName("PrimaryButton")
        self.package_button = QPushButton(tr("一键打包"))
        self.checkout_tag_button = QPushButton(tr("查看此版本"))
        self.reset_tag_button = QPushButton(tr("强制回退到此版本"))
        self.reset_tag_button.setObjectName("DangerButton")
        for index, button in enumerate(
            [
                self.commit_button,
                self.release_button,
                self.package_button,
                self.checkout_tag_button,
                self.reset_tag_button,
            ]
        ):
            buttons.addWidget(button, index // 3, index % 3)

        layout.addWidget(self.version_info_box)
        layout.addWidget(self.version_actions_box)
        self.commit_button.clicked.connect(self.commit_version)
        self.release_button.clicked.connect(self.release_version)
        self.package_button.clicked.connect(self.package_only)
        self.checkout_tag_button.clicked.connect(self.checkout_tag)
        self.reset_tag_button.clicked.connect(self.reset_tag)
        self.action_buttons.extend(
            [
                self.commit_button,
                self.release_button,
                self.package_button,
                self.checkout_tag_button,
                self.reset_tag_button,
            ]
        )
        return widget

    def _build_branch_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.branch_box, box_layout = self._card(tr("分支操作"))
        self.open_branch_button = QPushButton(tr("打开分支管理"))
        self.open_branch_button.setObjectName("PrimaryButton")
        self.branch_desc_label = QLabel(tr("支持创建、切换、删除、强制删除和合并分支。"))
        box_layout.addWidget(self.branch_desc_label)
        box_layout.addWidget(self.open_branch_button)
        layout.addWidget(self.branch_box)
        self.open_branch_button.clicked.connect(self.open_branch_dialog)
        self.action_buttons.append(self.open_branch_button)
        return widget

    def _build_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.history_box, box_layout = self._card(tr("历史、Diff、回滚"))
        self.open_history_button = QPushButton(tr("打开提交历史"))
        self.open_history_button.setObjectName("PrimaryButton")
        self.history_desc_label = QLabel(tr("查看 commit、diff，支持安全 revert 和强制 reset。"))
        box_layout.addWidget(self.history_desc_label)
        box_layout.addWidget(self.open_history_button)
        layout.addWidget(self.history_box)
        self.open_history_button.clicked.connect(self.open_history_dialog)
        self.action_buttons.append(self.open_history_button)
        return widget

    def _build_compare_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.compare_box, box_layout = self._card(tr("版本之间不同点"))
        self.open_compare_button = QPushButton(tr("打开版本对比"))
        self.open_compare_button.setObjectName("PrimaryButton")
        self.compare_desc_label = QLabel(tr("选择两个 tag 或 HEAD，查看文件变更统计、提交差异和完整 diff。"))
        box_layout.addWidget(self.compare_desc_label)
        box_layout.addWidget(self.open_compare_button)
        layout.addWidget(self.compare_box)
        self.open_compare_button.clicked.connect(self.open_compare_dialog)
        self.action_buttons.append(self.open_compare_button)
        return widget

    def _build_project_compare_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.project_compare_box, box_layout = self._card(tr("任意工程目录不同点"))
        self.open_project_compare_button = QPushButton(tr("打开工程对比"))
        self.open_project_compare_button.setObjectName("PrimaryButton")
        self.project_compare_desc_label = QLabel(tr("选择任意两个工程目录，不依赖 Git，比较文件新增、删除、修改和代码 Diff。"))
        box_layout.addWidget(self.project_compare_desc_label)
        box_layout.addWidget(self.open_project_compare_button)
        layout.addWidget(self.project_compare_box)
        self.open_project_compare_button.clicked.connect(self.open_project_compare_dialog)
        self.action_buttons.append(self.open_project_compare_button)
        return widget

    def _build_clean_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.clean_box, box_layout = self._card(tr("STM32 工程清理"))
        self.clean_scan_button = QPushButton(tr("扫描可清理文件"))
        self.clean_button = QPushButton(tr("一键清理编译产物"))
        self.clean_button.setObjectName("DangerButton")
        self.clean_preview = QTextEdit()
        self.clean_preview.setReadOnly(True)
        self.clean_preview.setMinimumHeight(80)
        self.clean_preview.setMaximumHeight(110)
        box_layout.addWidget(self.clean_scan_button)
        box_layout.addWidget(self.clean_button)
        box_layout.addWidget(self.clean_preview)
        layout.addWidget(self.clean_box)
        self.clean_scan_button.clicked.connect(self.scan_clean_targets)
        self.clean_button.clicked.connect(self.clean_project)
        self.action_buttons.extend([self.clean_scan_button, self.clean_button])
        return widget

    def _build_remote_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.remote_box, box_layout = self._card(tr("远程同步"))
        self.pull_button = QPushButton("Pull")
        self.push_button = QPushButton("Push")
        self.push_tags_button = QPushButton("Push + Tags")
        self.set_remote_button = QPushButton(tr("应用远程地址"))
        self.verify_remote_button = QPushButton(tr("验证远程"))
        self.clone_remote_button = QPushButton(tr("从远程克隆"))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        for button in [
            self.pull_button,
            self.push_button,
            self.push_tags_button,
            self.set_remote_button,
            self.verify_remote_button,
            self.clone_remote_button,
        ]:
            row.addWidget(button)
        row.addStretch()
        box_layout.addLayout(row)
        self.remote_desc_label = QLabel(tr("远程地址可在设置中填写。Git 凭据不会弹出阻塞窗口，失败信息会写入日志。"))
        box_layout.addWidget(self.remote_desc_label)
        layout.addWidget(self.remote_box)
        self.pull_button.clicked.connect(self.pull_remote)
        self.push_button.clicked.connect(lambda: self.push_remote(False))
        self.push_tags_button.clicked.connect(lambda: self.push_remote(True))
        self.set_remote_button.clicked.connect(self.apply_remote)
        self.verify_remote_button.clicked.connect(self.verify_remote)
        self.clone_remote_button.clicked.connect(self.clone_remote)
        self.action_buttons.extend([
            self.pull_button,
            self.push_button,
            self.push_tags_button,
            self.set_remote_button,
            self.verify_remote_button,
            self.clone_remote_button,
        ])
        return widget

    def _build_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        self.settings_box, box_layout = self._card(tr("发布配置"))
        self.settings_button = QPushButton(tr("打开设置"))
        self.settings_button.setObjectName("PrimaryButton")
        self.cleanup_history_cache_button = QPushButton(tr("清理历史缓存"))
        self.cleanup_history_cache_button.setObjectName("DangerButton")
        self.help_button = make_help_box("FST-GIT发布工具V1.2 操作说明", self._main_help_steps())

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(self.settings_button)
        row.addWidget(self.cleanup_history_cache_button)
        row.addWidget(self.help_button)
        row.addStretch()
        self.settings_desc_label = QLabel(tr("配置固件目录、发布目录、源码目录、排除规则和远程地址。"))
        box_layout.addWidget(self.settings_desc_label)
        box_layout.addLayout(row)
        layout.addWidget(self.settings_box)
        self.settings_button.clicked.connect(self.open_settings)
        self.cleanup_history_cache_button.clicked.connect(self.cleanup_history_cache)
        self.action_buttons.extend([self.settings_button, self.cleanup_history_cache_button, self.help_button])
        return widget

    def _build_language_switch(self):
        self.language_switch = QWidget()
        layout = QHBoxLayout(self.language_switch)
        layout.setContentsMargins(6, 0, 2, 0)
        layout.setSpacing(4)
        self.language_combo_main = QComboBox()
        self.language_combo_main.setToolTip(tr("界面语言"))
        self.language_combo_main.setMinimumWidth(92)
        for code, label in LANGUAGE_OPTIONS:
            self.language_combo_main.addItem(label, code)
        index = self.language_combo_main.findData(self.config.get("language", "zh_CN"))
        if index >= 0:
            self.language_combo_main.setCurrentIndex(index)
        layout.addWidget(self.language_combo_main)
        self.tabs.setCornerWidget(self.language_switch)
        self.language_combo_main.currentIndexChanged.connect(self.apply_language)

    def _main_help_steps(self):
        return [
            "工具用途：FST-GIT发布工具V1.2 用于把 Git 初始化、提交、tag、Release 打包、回退、分支、清理、远程同步等操作封装成按钮，减少手写 Git 命令。",
            "基本流程：选择工程目录 -> 初始化工程 -> 修改代码 -> 提交版本 -> 发布 Release -> Push + Tags 到远程仓库。",
            "选择工程目录：左侧按钮。用于选择实际 STM32/Keil 工程根目录，不是选择远程仓库地址。选择后左侧会显示工程路径、分支、当前 tag 和工作区状态。",
            "刷新状态：重新读取当前工程的 Git 状态、分支、tag 和工作区是否干净。当你手动改文件、切换分支或外部执行 Git 后，可点击刷新。",
            "初始化工程：在当前工程目录执行 git init，生成 STM32 专用 .gitignore，提交 init STM32 project，并创建 v0.1 tag。只在新工程第一次使用时点击。",
            "返回分支：当你使用“查看历史版本”进入 detached HEAD 历史查看状态时，点击它返回 master/main/dev 等正常分支。",
            "检查工程：输出工程健康检查报告，包括 Git 仓库状态、当前分支、当前 tag、有效工程改动、远程仓库、固件文件和 .gitignore 规则。",
            "导出诊断包：把健康检查、配置、日志和 .gitignore 打包到 .stm32_git_tool/diagnostics/，用于排查问题。",
            "备份管理：查看和管理 backup/ 开头的备份分支。强制回退前工具会自动创建 backup 分支，误操作后可从这里恢复。",
            "显示/隐藏 Git目录：切换 .git 和 .stm32_git_tool 的隐藏/系统属性。需要手动查看目录时点“显示”，平时建议保持隐藏减少误删。",
            "版本号输入框：填写本次版本号，例如 v1.0、v1.1。发布 Release 时会作为 Git tag，不能和已有 tag 重复。",
            "修改说明输入框：填写本次修改内容。提交版本时会进入 commit message，发布包中也会写入 ReleaseNote。",
            "选择版本点下拉框：显示已有 tag 和全部 commit，可按版本号、日期或修改说明搜索。未发布的中间版本也可以直接查看或回退。",
            "提交版本：提交有效工程文件。工具会过滤 Keil 缓存、编译产物、日志、工具数据；提交前会弹出文件列表让你确认。",
            "发布 Release：正式发布版本。发布前会检查是否在正常分支、是否有未提交工程修改、tag 是否重复、是否找到 bin/hex 固件。通过后创建 tag 并生成 Release zip。",
            "一键打包：只生成 zip 发布包，不创建 tag，不代表正式发布。适合临时测试包。",
            "查看此版本：切换到选中的 tag 或 commit 查看旧版本文件。它只是查看，不是回退；查看后可以返回分支或直接执行强制回退。",
            "强制回退到此版本：把工程恢复到选中的 tag 或 commit。工具会检查未提交修改、要求保护密码和 RESET 确认，并自动创建 backup 分支。",
            "分支管理：打开分支弹窗，可创建、切换、删除、强制删除和合并分支。新功能建议先建分支，完成后合并回主分支。",
            "历史记录：打开提交历史弹窗，可查看 commit、代码 Diff、保存完整 Diff、安全回滚 Revert、强制回退 Reset。优先使用 Revert，只有需要整体恢复旧状态时才用 Reset。",
            "版本对比：选择旧版本和新版本，查看文件统计、提交差异、代码 Diff。绿色代表新增，红色代表删除，黄色代表代码位置提示。",
            "工程对比：选择任意两个本地工程目录，不依赖 Git，支持进度和取消、文件筛选、临时排除、改名识别和差异报告导出。",
            "工程清理：扫描并删除 Debug、Objects、Listings、map、axf、o、d 等编译产物。不会删除 .git、.stm32_git_tool 或源码文件。",
            "远程同步：先在设置里填写远程地址，再应用远程地址。Pull 拉取远程更新，Push 推送当前分支，Push + Tags 推送分支和 tag。",
            "设置：配置项目类型、固件目录、发布目录、源码目录、排除目录、排除文件、产物规则和远程地址。发布目录建议保持 .stm32_git_tool/releases。",
            ".git 保护：工具会隐藏 .git 和 .stm32_git_tool，减少误删。如果 .git 被人为删除，优先从远程 clone 恢复，不建议重新 init。",
            "保护密码：第一次执行强制回退类危险操作时由你自己设置。以后 Reset/强制回退需要输入该密码和 RESET 二次确认。",
        ]

    def log(self, message):
        message = tr(str(message))
        self.log_signal.emit(message)
        try:
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)
            with open(self.log_file_path, "a", encoding="utf-8") as file:
                file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n")
        except OSError:
            pass

    def _make_log_file_path(self):
        log_dir = tool_file(self.project_path, "logs")
        return os.path.join(log_dir, f"tool_{datetime.now():%Y%m%d}.log")

    def _startup_project_path(self):
        last_path = self.app_state.get("last_project_path", "")
        if last_path and os.path.isdir(last_path):
            return os.path.realpath(last_path)
        return os.getcwd()

    def _append_log(self, message):
        self.log_text.append(str(message))
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _set_busy(self, busy):
        self.busy_count = max(0, self.busy_count + (1 if busy else -1))
        is_busy = self.busy_count > 0
        for button in self.action_buttons + [self.init_button, self.refresh_button, self.select_path_button, self.health_button, self.diagnostics_button, self.backup_button, self.toggle_git_dirs_button]:
            button.setEnabled(not is_busy)
        self._update_return_branch_button()
        self.repo_label.setText(("Running..." if self.config.get("language") == "en_US" else "正在执行...") if is_busy else self.last_repo_text)

    def select_project_path(self):
        dialog_title = "Select STM32 Project Folder" if self.config.get("language") == "en_US" else "选择 STM32 工程目录"
        path = QFileDialog.getExistingDirectory(self, dialog_title, self.project_path)
        if not path:
            return
        self.project_path = path
        self.path_label.setText(path)
        self.git.set_project_path(path)
        ensure_tool_dir(path)
        protect_repository_dirs(path, self.log)
        self.config_manager = ConfigManager(tool_file(path, "app_config.json"))
        self.config = self.config_manager.load()
        self.app_state_manager.save_last_project(path)
        self.app_state = self.app_state_manager.load()
        set_language(self.config.get("language", "zh_CN"))
        self.log_file_path = self._make_log_file_path()
        self.log(f"[Project] Selected {path}" if self.config.get("language") == "en_US" else f"[工程] 已选择 {path}")
        self.check_repo_guard()
        self.refresh_status()

    def run_async(self, func, refresh=False, on_finished=None):
        worker = TaskWorker(func)
        self.busy_signal.emit(True)
        worker.signals.error.connect(lambda text: self.log(f"[错误] {text}"))
        worker.signals.error.connect(lambda _: self.busy_signal.emit(False))
        worker.signals.finished.connect(lambda result: self.busy_signal.emit(False))
        if refresh:
            worker.signals.finished.connect(lambda _: self.refresh_status())
        if on_finished:
            worker.signals.finished.connect(on_finished)
        self.thread_pool.start(worker)

    def refresh_status(self):
        self.path_label.setText(self.project_path)

        def task():
            if not self.git.is_repository():
                return {
                    "repo": False,
                    "branch": "-",
                    "tag": "-",
                    "dirty": "-",
                    "refs": [],
                    "current_ref": "",
                    "current_commit": "",
                }
            current_tag = self.git.current_tag()
            return {
                "repo": True,
                "branch": self.git.current_branch(),
                "tag": current_tag or "-",
                "dirty": ("Meaningful changes" if self.config.get("language") == "en_US" else "有有效工程改动") if self.git.meaningful_changed_files() else ("Clean" if self.config.get("language") == "en_US" else "干净"),
                "refs": [item for item in self.git.list_compare_refs() if item["kind"] != "head"],
                "current_ref": current_tag,
                "current_commit": self.git.resolve_commit("HEAD"),
            }

        worker = TaskWorker(task)
        worker.signals.finished.connect(self.status_signal.emit)
        worker.signals.error.connect(lambda text: self.log(f"[状态刷新失败] {text}"))
        self.thread_pool.start(worker)

    def _apply_status(self, status):
        self.last_status = status
        self.last_repo_text = "Git repository ready" if status["repo"] else tr("当前目录不是 Git 仓库")
        self.repo_label.setText(self.last_repo_text)
        self.branch_label.setText(status["branch"])
        self.tag_label.setText(status["tag"])
        self.dirty_label.setText(status["dirty"])
        self.tag_combo.set_refs(status["refs"])
        for current_ref in [status.get("current_ref"), status.get("current_commit")]:
            if not current_ref:
                continue
            if self.tag_combo.set_current_ref(current_ref):
                break
        if not status["repo"]:
            self.log("[提示] 当前目录没有 .git，可点击“初始化工程”。")
        self._update_return_branch_button()
        self._update_git_dirs_button()

    def _update_return_branch_button(self):
        self.return_branch_button.setEnabled(
            self.last_status.get("repo", False)
            and self.last_status.get("branch") == "(detached)"
            and self.busy_count == 0
        )

    def _update_git_dirs_button(self):
        if repository_dirs_hidden(self.project_path):
            self.toggle_git_dirs_button.setText(tr("显示 Git目录"))
        else:
            self.toggle_git_dirs_button.setText(tr("隐藏 Git目录"))

    def toggle_git_dirs_visibility(self):
        if not os.path.isdir(os.path.join(self.project_path, ".git")):
            QMessageBox.information(self, tr("未找到 Git 目录"), tr("当前工程目录下没有 .git。"))
            return
        if repository_dirs_hidden(self.project_path):
            show_repository_dirs(self.project_path, self.log)
            self.log("[Git目录] 已显示 .git 和 .stm32_git_tool。")
        else:
            protect_repository_dirs(self.project_path, self.log)
            self.log("[Git目录] 已隐藏 .git 和 .stm32_git_tool。")
        self._update_git_dirs_button()

    def _validate_version(self):
        version = normalize_version(self.version_input.text())
        if not version:
            QMessageBox.warning(self, tr("缺少版本号"), tr("请输入版本号，例如 v1.2"))
            return ""
        self.version_input.setText(version)
        if not is_valid_version(version):
            QMessageBox.warning(self, "Version format" if self.config.get("language") == "en_US" else "版本号格式不规范", version_help())
            return ""
        return version

    def _require_repository(self) -> bool:
        if self.git.is_repository():
            return True
        QMessageBox.information(self, tr("当前目录不是 Git 仓库"), tr("当前目录不是 Git 仓库。请先选择正确工程目录，或点击“初始化工程”。"))
        return False

    def _merge_gitignore(self):
        gitignore_path = os.path.join(self.project_path, ".gitignore")
        ensure_writable_file(gitignore_path, self.log)
        existing_lines = []
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as file:
                existing_lines = [line.rstrip("\n") for line in file]
        merged = existing_lines[:]
        for line in STM32_GITIGNORE_LINES:
            if line not in merged:
                merged.append(line)
        try:
            with open(gitignore_path, "w", encoding="utf-8") as file:
                file.write("\n".join(merged).strip() + "\n")
        except PermissionError as exc:
            raise PermissionError(
                f"无法写入 .gitignore，请检查文件是否被占用、只读，或当前账号是否有工程目录写权限：{gitignore_path}"
            ) from exc

    def _ensure_local_ignore_rules(self):
        if not self.git.is_repository():
            return
        before = ""
        gitignore_path = os.path.join(self.project_path, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as file:
                before = file.read()
        self._merge_gitignore()
        after = ""
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8", errors="replace") as file:
                after = file.read()
        if before != after:
            self.log("[提示] 已更新 .gitignore，忽略 .stm32_git_tool/ 工具数据目录。请提交一次 .gitignore 变更。")
        RepoGuard(self.project_path, self.git).save(self.config.get("remote", ""))
        protect_repository_dirs(self.project_path, self.log)

    def init_project(self):
        def task():
            self.git.init_project()
            self._merge_gitignore()
            self.git.add_all()
            result = self.git.commit("init STM32 project")
            if not result.ok:
                self.log("[提示] 初始化提交没有生成新 commit，可能已经提交过。")
            if "v0.1" not in self.git.list_tags():
                self.git.tag("v0.1")
            RepoGuard(self.project_path, self.git).save(self.config.get("remote", ""))
            protect_repository_dirs(self.project_path, self.log)

        self.run_async(task, refresh=True)

    def commit_version(self):
        version = self._validate_version()
        if not version:
            return
        if not self._require_repository():
            return
        if self.git.current_branch() == "(detached)":
            self.create_work_branch_then(
                "提交版本",
                version,
                self.commit_version,
                prompt_for_name=False,
            )
            return
        desc = self.desc_input.text().strip() or "update"
        message = f"{version} - {desc}"

        def prepare():
            if not self.git.is_repository():
                raise RuntimeError("当前目录不是 Git 仓库，请先初始化工程。")
            self._ensure_local_ignore_rules()
            changes = self.git.changed_files()
            if not changes:
                return {"changes": [], "meaningful": []}
            meaningful_paths = self.git.meaningful_changed_files()
            return {"changes": changes, "meaningful": meaningful_paths}

        def after_prepare(info):
            changes = info["changes"]
            meaningful_paths = info["meaningful"]
            if not changes:
                self.log("[提示] 没有检测到未提交文件。")
                return
            self.log("[变更文件]")
            for item in changes:
                self.log(f"  {item}")
            if not meaningful_paths:
                self.log("[提示] 检测到的都是 Keil 缓存/日志/发布包等非工程改动，不执行提交。")
                return
            self.log("[本次提交的有效工程文件]")
            for item in meaningful_paths:
                self.log(f"  {item}")
            if not self.confirm_file_list("确认提交版本", "本次将提交以下有效工程文件：", meaningful_paths):
                self.log("[取消] 用户取消提交。")
                return
            self.run_async(lambda: do_commit(meaningful_paths), refresh=True)

        def do_commit(meaningful_paths):
            self.git.add_paths(meaningful_paths)
            if not self.git.has_staged_changes():
                self.log("[提示] git add 后暂存区没有实际内容，不执行提交。")
                return
            result = self.git.commit(message)
            if not result.ok:
                raise RuntimeError(result.stderr.strip() or "提交失败")

        self.run_async(prepare, on_finished=after_prepare)

    def release_version(self):
        version = self._validate_version()
        if not version:
            return
        if not self._require_repository():
            return
        if self.git.current_branch() == "(detached)":
            self.create_work_branch_then("发布 Release", version, self.release_version)
            return
        desc = self.desc_input.text().strip()

        def task():
            if not self.git.is_repository():
                raise RuntimeError("当前目录不是 Git 仓库，请先初始化工程。")
            self._ensure_local_ignore_rules()
            branch = self.git.current_branch()
            if branch == "(detached)":
                raise RuntimeError("当前处于历史查看模式 detached HEAD，不能发布 Release。请先点击“返回分支”。")
            changes = self.git.changed_files()
            meaningful_paths = self.git.meaningful_changed_files()
            if meaningful_paths:
                self.log("[有效工程变更文件]")
                for item in meaningful_paths:
                    self.log(f"  {item}")
                raise RuntimeError("发布前检查失败：当前存在未提交工程修改。请先“提交版本”后再发布 Release。")
            if changes:
                self.log("[提示] 仅检测到 Keil 缓存/日志/发布包等非工程改动，不影响 Release。")
            firmware_files = self._firmware_files()
            tags = self.git.list_tags()
            if version in tags:
                raise RuntimeError(f"发布前检查失败：tag {version} 已存在。请换一个版本号，或确认该版本是否已发布。")
            if not firmware_files:
                raise RuntimeError("发布前检查失败：未找到 .bin 或 .hex 固件文件。请先编译工程，或在设置中配置固件目录。")
            if not self.config.get("remote", "").strip():
                self.log("[提示] 未配置远程仓库，本次只生成本地 Release 包。")
            self.log("[发布前检查通过]")
            self.log(f"  当前分支: {branch}")
            self.log(f"  版本号: {version}")
            self.log(f"  固件文件: {len(firmware_files)} 个")
            for firmware in firmware_files[:10]:
                self.log(f"    {firmware}")
            if len(firmware_files) > 10:
                self.log(f"    ... 另有 {len(firmware_files) - 10} 个")
            archive = self._create_package(version, desc, firmware_files)
            try:
                self.git.tag(version)
            except Exception:
                try:
                    os.remove(archive)
                except OSError:
                    pass
                raise
            self.log(f"[Release 完成] {archive}")

        self.run_async(task, refresh=True)

    def create_work_branch_then(self, action_name, version, continue_action, prompt_for_name=True):
        branches = set(self.git.list_branches())
        base_name = f"work/{version}"
        branch_name = base_name
        suffix = 1
        while branch_name in branches:
            suffix += 1
            branch_name = f"{base_name}-{suffix}"

        if prompt_for_name:
            branch, ok = QInputDialog.getText(
                self,
                tr("创建工作分支后") + tr(action_name),
                tr("当前处于历史查看模式 detached HEAD，不能直接提交或发布。\n"
                "工具将基于当前代码位置创建一个正常分支，然后自动继续刚才的操作。\n\n"
                "请输入新分支名："),
                text=branch_name,
            )
            branch = branch.strip()
            if not ok:
                return
        else:
            branch = branch_name
            self.log(f"[自动创建工作分支] {branch}")

        if not branch:
            QMessageBox.warning(self, tr("分支名不能为空"), tr("请输入一个分支名。"))
            return
        if any(char.isspace() for char in branch):
            QMessageBox.warning(self, tr("分支名不合法"), tr("分支名不能包含空白字符。"))
            return
        if branch in branches:
            QMessageBox.warning(self, tr("分支已存在"), tr("分支 {branch} 已存在，请换一个新分支名。", branch=branch))
            return

        self.run_async(
            lambda: self.git.create_and_checkout_branch(branch),
            refresh=True,
            on_finished=lambda _: continue_action(),
        )

    def recover_branch_before_release(self):
        if not self._require_repository():
            return

        def apply(branches):
            if branches:
                preferred = next((branch for branch in ["master", "main", "dev"] if branch in branches), branches[0])
                branch, ok = QInputDialog.getItem(
                    self,
                    tr("返回分支后发布"),
                    tr("当前处于历史查看模式，正式发布需要先回到正常分支。\n选择要返回的分支："),
                    branches,
                    branches.index(preferred),
                    False,
                )
                if ok and branch:
                    self.run_async(lambda: self.git.checkout_branch(branch), refresh=True)
                return

            branch, ok = QInputDialog.getText(
                self,
                tr("创建发布分支"),
                tr("当前没有任何正常分支，不能直接发布 Release。\n请输入要基于当前位置创建的分支名："),
                text="master",
            )
            branch = branch.strip()
            if branch and any(char.isspace() for char in branch):
                QMessageBox.warning(self, tr("分支名不合法"), tr("分支名不能包含空白字符。"))
                return
            if ok and branch:
                self.run_async(
                    lambda: self.git.create_and_checkout_branch(branch),
                    refresh=True,
                    on_finished=lambda _: QMessageBox.information(
                        self,
                        tr("已创建发布分支"),
                        tr("已创建并切换到分支：{branch}\n\n请先提交版本，再点击“发布 Release”。", branch=branch),
                    ),
                )

        self.run_async(self.git.list_branches, on_finished=apply)

    def package_only(self):
        version = self._validate_version()
        if not version:
            return
        desc = self.desc_input.text().strip()
        self.run_async(lambda: self._create_package(version, desc), refresh=False)

    def _firmware_files(self):
        configured = self.config.get("firmware_dir", "")
        patterns = self.config.get("firmware_patterns", ["*.bin", "*.hex"])
        if configured:
            firmware_dir = configured if os.path.isabs(configured) else os.path.join(self.project_path, configured)
            files = []
            if os.path.isdir(firmware_dir):
                for root, _, filenames in os.walk(firmware_dir):
                    for filename in filenames:
                        if any(self._matches_pattern(filename.lower(), pattern.lower()) for pattern in patterns):
                            files.append(os.path.join(root, filename))
            return files
        return ProjectScanner(self.project_path).find_firmware_files()

    @staticmethod
    def _matches_pattern(name, pattern):
        if pattern.startswith("*."):
            return name.endswith(pattern[1:])
        return name == pattern

    def _create_package(self, version, desc, firmware_files=None):
        packager = ReleasePackager(self.project_path, self.config, self.log)
        return packager.create_release(version, desc, firmware_files if firmware_files is not None else self._firmware_files())

    def confirm_file_list(self, title, intro, paths):
        preview = "\n".join(paths[:40])
        if len(paths) > 40:
            preview += f"\n... 另有 {len(paths) - 40} 个文件"
        return QMessageBox.question(self, tr(title), f"{tr(intro)}\n\n{preview}") == QMessageBox.Yes

    def _check_dirty_then(self, action, dirty_text, block_dirty=False):
        def after_check(changes):
            if changes and block_dirty:
                self.log("[有效工程变更文件]")
                for item in changes:
                    self.log(f"  {item}")
                QMessageBox.warning(self, tr("存在未提交修改"), tr(dirty_text))
                return
            if changes:
                self.log("[有效工程变更文件]")
                for item in changes:
                    self.log(f"  {item}")
                reply = QMessageBox.question(self, tr("存在未提交修改"), tr(dirty_text))
                if reply != QMessageBox.Yes:
                    return
            self.run_async(action, refresh=True)

        self.run_async(self.git.meaningful_changed_files, on_finished=after_check)

    def checkout_tag(self):
        if not self._require_repository():
            return
        ref = self.tag_combo.current_ref()
        if not ref:
            QMessageBox.information(self, tr("没有版本点"), tr("请从下拉列表中选择一个有效版本点。"))
            return
        self._check_dirty_then(
            lambda: self.git.checkout_force(str(ref)),
            "当前存在未提交修改，仍要切换到所选版本点吗？",
            block_dirty=False,
        )

    def reset_tag(self):
        if not self._require_repository():
            return
        ref = self.tag_combo.current_ref()
        if not ref:
            QMessageBox.information(self, tr("没有版本点"), tr("请从下拉列表中选择一个有效版本点。"))
            return
        target_label = self.tag_combo.currentText().strip()
        current = self.git.current_tag() or self.git.current_branch()
        if QMessageBox.question(
            self,
            tr("危险操作"),
            tr("确认强制回退？\n\n当前位置：{current}\n目标版本：{tag}\n\n工具会先创建 backup 分支，回退错误时可从“备份管理”恢复。", current=current, tag=target_label),
        ) != QMessageBox.Yes:
            return
        if not self.verify_dangerous_operation("强制回退到版本点"):
            return
        self._check_dirty_then(
            lambda: self.reset_with_backup(str(ref)),
            "请先提交、暂存或放弃当前修改后再强制回退。",
            block_dirty=True,
        )

    def scan_clean_targets(self):
        def apply_targets(targets):
            self.clean_preview.setPlainText("\n".join(targets) if targets else tr("没有发现可清理项"))

        cleaner = ProjectCleaner(self.project_path, self.log)
        self.run_async(cleaner.scan, on_finished=apply_targets)

    def clean_project(self):
        cleaner = ProjectCleaner(self.project_path, self.log)

        def confirm_and_clean(targets):
            if not targets:
                self.clean_preview.setPlainText(tr("没有发现可清理项"))
                return
            self.clean_preview.setPlainText("\n".join(targets))
            if QMessageBox.question(self, tr("确认清理"), tr("确认删除 {count} 个编译产物？", count=len(targets))) != QMessageBox.Yes:
                return
            self.run_async(cleaner.clean, refresh=False)

        self.run_async(cleaner.scan, on_finished=confirm_and_clean)

    def apply_remote(self):
        if not self._require_repository():
            return
        remote = self.config.get("remote", "").strip()
        if not remote:
            QMessageBox.information(self, tr("未配置远程地址"), tr("请先在设置中填写远程地址。"))
            return

        def task():
            result = self.git.run(["remote", "get-url", "origin"])
            if result.ok:
                out = self.git.run(["remote", "set-url", "origin", remote], check=True)
            else:
                out = self.git.run(["remote", "add", "origin", remote], check=True)
            RepoGuard(self.project_path, self.git).save(remote)
            protect_repository_dirs(self.project_path, self.log)
            return out

        self.run_async(task, refresh=True)

    def verify_remote(self):
        remote = self.config.get("remote", "").strip()
        if not remote:
            QMessageBox.information(self, tr("未配置远程地址"), tr("请先在设置中填写远程地址。"))
            return
        self.run_async(lambda: self.git.run(["ls-remote", remote], check=True), on_finished=lambda _: QMessageBox.information(self, tr("验证通过"), tr("远程仓库地址可访问。")))

    def clone_remote(self):
        remote = self.config.get("remote", "").strip()
        if not remote:
            QMessageBox.information(self, tr("未配置远程地址"), tr("请先在设置中填写远程地址。"))
            return
        parent = QFileDialog.getExistingDirectory(self, tr("选择克隆目标父目录"), os.path.dirname(self.project_path))
        if not parent:
            return
        name, ok = QInputDialog.getText(self, tr("目标目录名"), tr("留空则使用仓库名："))
        if not ok:
            return
        self.run_async(lambda: Recovery.clone(remote, parent, name), on_finished=lambda path: QMessageBox.information(self, tr("克隆完成"), path))

    def pull_remote(self):
        if not self._require_repository():
            return
        self.run_async(self.git.pull, refresh=True)

    def push_remote(self, push_tags=False):
        if not self._require_repository():
            return
        self.run_async(lambda: self.git.push(push_tags), refresh=True)

    def cleanup_history_cache(self):
        if not self._require_repository():
            return
        if QMessageBox.question(
            self,
            tr("确认清理历史缓存"),
            tr("该操作会清理 Git reflog 和无引用对象，减小仓库缓存体积。\n\n"
            "不会删除当前分支、tag 或正常提交历史。\n"
            "已经没有分支或 tag 引用的临时对象可能会被永久清理。\n\n"
            "确认继续？"),
        ) != QMessageBox.Yes:
            return
        self.run_async(self.git.cleanup_history_cache, refresh=True)

    def reset_with_backup(self, ref):
        backup = BackupManager(self.git).create_backup("before-reset")
        self.log(f"[备份分支] 已创建 {backup}")
        restore_branch = self._next_restore_branch_name(ref)
        was_detached = self.git.current_branch() == "(detached)"
        result = self.git.reset_hard_attached(ref, restore_branch)
        if not result.ok:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "强制回退失败")
        if was_detached:
            self.log(f"[恢复分支] 已创建并切换到 {restore_branch}")
        self.log(f"[恢复提示] 如果回退错误，可在“备份管理”中恢复 {backup}")
        return result

    def _next_restore_branch_name(self, ref):
        ref_text = str(ref).strip()
        ref_label = ref_text[:8] if len(ref_text) >= 12 and all(char in "0123456789abcdefABCDEF" for char in ref_text) else ref_text
        safe_ref = "".join(char if char.isalnum() or char in "._-" else "-" for char in ref_label).strip("-")
        base_name = f"work/restore-{safe_ref or 'version'}"
        branches = set(self.git.list_branches())
        branch_name = base_name
        suffix = 2
        while branch_name in branches:
            branch_name = f"{base_name}-{suffix}"
            suffix += 1
        return branch_name

    def ensure_protection_password(self):
        if protection_enabled(self.config):
            return True
        password, ok = QInputDialog.getText(self, tr("设置保护密码"), tr("首次危险操作需要设置保护密码："), QLineEdit.Password)
        if not ok or not password:
            return False
        confirm, ok = QInputDialog.getText(self, tr("确认保护密码"), tr("再次输入保护密码："), QLineEdit.Password)
        if not ok or password != confirm:
            QMessageBox.warning(self, tr("密码不一致"), tr("两次输入的保护密码不一致。"))
            return False
        self.config.update(hash_password(password))
        self.config["protection_enabled"] = True
        self.config_manager.save(self.config)
        return True

    def verify_dangerous_operation(self, action_name):
        if not self.ensure_protection_password():
            return False
        password, ok = QInputDialog.getText(self, tr("危险操作确认"), tr("{action}\n请输入保护密码：", action=tr(action_name)), QLineEdit.Password)
        if not ok or not verify_password(password, self.config):
            QMessageBox.warning(self, tr("密码错误"), tr("保护密码不正确。"))
            return False
        token, ok = QInputDialog.getText(self, tr("二次确认"), tr("请输入 RESET 确认执行："))
        if not ok or token != "RESET":
            QMessageBox.information(self, tr("已取消"), tr("未输入 RESET，操作已取消。"))
            return False
        return True

    def check_repo_guard(self):
        guard = RepoGuard(self.project_path, self.git)
        status = guard.status()
        if status == "missing_git":
            data = guard.load()
            remote = data.get("remote_url", "") or self.config.get("remote", "")
            message = "检测到 .git 仓库信息丢失。\n\n建议优先从远程仓库重新 clone 恢复。"
            if remote:
                message += f"\n\n远程仓库：{remote}"
            QMessageBox.warning(self, tr("Git 仓库丢失"), tr(message))
            self.log("[警告] .stm32_git_tool/.git_guard.json 存在，但 .git 目录不存在。")
        elif status == "unguarded":
            guard.save(self.config.get("remote", ""))
            protect_repository_dirs(self.project_path, self.log)
            self.log("[仓库保护] 已创建 .stm32_git_tool/.git_guard.json。")

    def return_to_branch(self):
        if not self._require_repository():
            return

        def apply(branches):
            if not branches:
                branch, ok = QInputDialog.getText(
                    self,
                    tr("创建恢复分支"),
                    tr("当前没有可返回的分支。\n请输入要基于当前位置创建的分支名："),
                    text="master",
                )
                branch = branch.strip()
                if branch and any(char.isspace() for char in branch):
                    QMessageBox.warning(self, tr("分支名不合法"), tr("分支名不能包含空白字符。"))
                    return
                if ok and branch:
                    self.run_async(lambda: self.git.create_and_checkout_branch(branch), refresh=True)
                return
            preferred = next((branch for branch in ["master", "main", "dev"] if branch in branches), branches[0])
            branch, ok = QInputDialog.getItem(self, tr("返回分支"), tr("选择要返回的分支："), branches, branches.index(preferred), False)
            if ok and branch:
                self.run_async(lambda: self.git.checkout_branch(branch), refresh=True)

        self.run_async(self.git.list_branches, on_finished=apply)

    def run_health_check(self):
        diagnostics = Diagnostics(self.project_path, self.git, self.config)
        self.run_async(lambda: diagnostics.health_report(), on_finished=self._set_log_text)

    def export_diagnostics(self):
        diagnostics = Diagnostics(self.project_path, self.git, self.config)

        def done(path):
            self.log(f"[诊断包] {path}")
            QMessageBox.information(self, tr("诊断包已导出"), path)

        self.run_async(lambda: diagnostics.export_diagnostics(self.log_file_path), on_finished=done)

    def _set_log_text(self, text):
        self.log_text.setPlainText(tr(text))
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _retranslate_ui(self):
        self.setWindowTitle(tr("FST-GIT发布工具V1.2"))
        self.title_label.setText(tr("FST-GIT发布工具V1.2"))
        self.subtitle_label.setText(tr("Git 版本管理 / 清理 / Release 打包"))
        self.repo_label.setText(tr(self.last_repo_text))
        self.select_path_button.setText(tr("选择工程目录"))
        self.refresh_button.setText(tr("刷新状态"))
        self.init_button.setText(tr("初始化工程"))
        self.return_branch_button.setText(tr("返回分支"))
        self.health_button.setText(tr("检查工程"))
        self.diagnostics_button.setText(tr("导出诊断包"))
        self.backup_button.setText(tr("备份管理"))
        self.path_title_label.setText(tr("工程路径"))
        self.branch_title_label.setText(tr("当前分支"))
        self.tag_title_label.setText(tr("当前 tag"))
        self.dirty_title_label.setText(tr("工作区状态"))
        self.tabs.setTabText(0, tr("版本发布"))
        self.tabs.setTabText(1, tr("分支管理"))
        self.tabs.setTabText(2, tr("历史记录"))
        self.tabs.setTabText(3, tr("版本对比"))
        self.tabs.setTabText(4, tr("工程对比"))
        self.tabs.setTabText(5, tr("工程清理"))
        self.tabs.setTabText(6, tr("远程同步"))
        self.tabs.setTabText(7, tr("设置"))
        self.log_text.setPlaceholderText(tr("Git 命令、清理、打包、错误输出都会显示在这里。"))
        self.log_box.setTitle(tr("执行日志"))
        self.clear_log_button.setText(tr("清空日志"))
        self.version_info_box.setTitle(tr("版本信息"))
        self.version_title_label.setText(tr("版本号"))
        self.desc_title_label.setText(tr("修改说明"))
        self.tag_select_title_label.setText(tr("选择版本点"))
        self.version_actions_box.setTitle(tr("版本操作"))
        self.version_input.setPlaceholderText(tr("例如 v1.2"))
        self.desc_input.setPlaceholderText(tr("修改说明，例如 修复串口通信问题"))
        self.commit_button.setText(tr("提交版本"))
        self.release_button.setText(tr("发布 Release"))
        self.package_button.setText(tr("一键打包"))
        self.checkout_tag_button.setText(tr("查看此版本"))
        self.reset_tag_button.setText(tr("强制回退到此版本"))
        self.branch_box.setTitle(tr("分支操作"))
        self.branch_desc_label.setText(tr("支持创建、切换、删除、强制删除和合并分支。"))
        self.open_branch_button.setText(tr("打开分支管理"))
        self.history_box.setTitle(tr("历史、Diff、回滚"))
        self.history_desc_label.setText(tr("查看 commit、diff，支持安全 revert 和强制 reset。"))
        self.open_history_button.setText(tr("打开提交历史"))
        self.compare_box.setTitle(tr("版本之间不同点"))
        self.compare_desc_label.setText(tr("选择两个 tag 或 HEAD，查看文件变更统计、提交差异和完整 diff。"))
        self.open_compare_button.setText(tr("打开版本对比"))
        self.project_compare_box.setTitle(tr("任意工程目录不同点"))
        self.project_compare_desc_label.setText(tr("选择任意两个工程目录，不依赖 Git，比较文件新增、删除、修改和代码 Diff。"))
        self.open_project_compare_button.setText(tr("打开工程对比"))
        self.clean_box.setTitle(tr("STM32 工程清理"))
        self.clean_scan_button.setText(tr("扫描可清理文件"))
        self.clean_button.setText(tr("一键清理编译产物"))
        self.remote_box.setTitle(tr("远程同步"))
        self.set_remote_button.setText(tr("应用远程地址"))
        self.verify_remote_button.setText(tr("验证远程"))
        self.clone_remote_button.setText(tr("从远程克隆"))
        self.remote_desc_label.setText(tr("远程地址可在设置中填写。Git 凭据不会弹出阻塞窗口，失败信息会写入日志。"))
        self.settings_box.setTitle(tr("发布配置"))
        self.settings_button.setText(tr("打开设置"))
        self.cleanup_history_cache_button.setText(tr("清理历史缓存"))
        self.settings_desc_label.setText(tr("配置固件目录、发布目录、源码目录、排除规则和远程地址。"))
        self.language_combo_main.setToolTip(tr("界面语言"))
        self.help_button.setText(tr("操作说明"))
        self.help_button.setToolTip(tr("FST-GIT发布工具V1.2 操作说明"))
        self._update_git_dirs_button()

    def apply_language(self, _index=None):
        language = self.language_combo_main.currentData()
        self.config["language"] = language
        set_language(language)
        self.config_manager.save(self.config)
        self._retranslate_ui()
        self.refresh_status()
        self.log("[Settings] Language updated" if language == "en_US" else "[设置] 已更新界面语言")

    def open_branch_dialog(self):
        if not self._require_repository():
            return
        BranchDialog(self.git, self.refresh_status, self).exec_()

    def open_history_dialog(self):
        if not self._require_repository():
            return
        HistoryDialog(
            self.git,
            self.refresh_status,
            reset_callback=self.reset_with_backup,
            verify_callback=self.verify_dangerous_operation,
            parent=self,
        ).exec_()

    def open_compare_dialog(self):
        if not self._require_repository():
            return
        CompareDialog(self.git, self).exec_()

    def open_project_compare_dialog(self):
        ProjectCompareDialog(self.project_path, self.config, self).exec_()

    def open_backup_dialog(self):
        if not self._require_repository():
            return
        BackupDialog(self.git, self.refresh_status, verify_callback=self.verify_dangerous_operation, parent=self).exec_()

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_():
            self.config = dialog.get_config()
            set_language(self.config.get("language", "zh_CN"))
            index = self.language_combo_main.findData(self.config.get("language", "zh_CN"))
            if index >= 0:
                self.language_combo_main.blockSignals(True)
                self.language_combo_main.setCurrentIndex(index)
                self.language_combo_main.blockSignals(False)
            self.config_manager.save(self.config)
            self._retranslate_ui()
            self.refresh_status()
            self.log("[Settings] Saved" if self.config.get("language") == "en_US" else "[设置] 已保存")
            QMessageBox.information(self, tr("设置"), tr("设置已保存。"))

    def closeEvent(self, event):
        self.app_state_manager.save_last_project(self.project_path)
        self.thread_pool.waitForDone(1000)
        super().closeEvent(event)
