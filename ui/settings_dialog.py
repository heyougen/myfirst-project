from PyQt5.QtWidgets import (
    QDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

try:
    from core.project_templates import get_template, template_names
    from ui.help_widgets import make_help_box
except ModuleNotFoundError:
    from stm32_git_release_tool.core.project_templates import get_template, template_names
    from stm32_git_release_tool.ui.help_widgets import make_help_box


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(680, 300)
        self.config = config.copy()

        self.project_type = QComboBox()
        self.project_type.addItems(template_names())
        current_type = self.config.get("project_type", "STM32 Keil")
        if current_type in template_names():
            self.project_type.setCurrentText(current_type)
        self.firmware_dir = QLineEdit(self.config.get("firmware_dir", ""))
        self.release_dir = QLineEdit(self.config.get("release_dir", ".stm32_git_tool/releases"))
        self.include_dirs = QLineEdit(",".join(self.config.get("include_source_dirs", [])))
        self.exclude_dirs = QLineEdit(",".join(self.config.get("exclude_dirs", [])))
        self.exclude_patterns = QLineEdit(",".join(self.config.get("exclude_patterns", [])))
        self.firmware_patterns = QLineEdit(",".join(self.config.get("firmware_patterns", [])))
        self.remote = QLineEdit(self.config.get("remote", ""))

        form = QFormLayout()
        form.addRow("项目类型", self.project_type)
        form.addRow("固件目录", self.firmware_dir)
        form.addRow("发布目录", self.release_dir)
        form.addRow("源码目录", self.include_dirs)
        form.addRow("排除目录", self.exclude_dirs)
        form.addRow("排除文件", self.exclude_patterns)
        form.addRow("产物规则", self.firmware_patterns)
        form.addRow("远程地址", self.remote)

        self.ok_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.ok_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(make_help_box("设置说明", [
            "项目类型：选择工程模板。STM32 Keil 会自动排除 Debug、Objects、Listings 和 Keil 用户缓存文件。",
            "固件目录：填写 bin/hex 所在目录。留空时工具会扫描整个工程；指定后只扫描该目录。",
            "发布目录：Release zip 输出位置。建议保持 .stm32_git_tool/releases，避免污染工程根目录。",
            "源码目录：Release 包中 src 要包含的目录。多个目录用英文逗号分隔，例如 Core,Drivers,MDK-ARM。",
            "排除目录：不会提交或打包的目录，例如 .git,.stm32_git_tool,Debug,Objects,Listings。",
            "排除文件：不会提交或打包的文件规则，例如 *.map,*.axf,*.uvguix.*。",
            "产物规则：识别固件文件的规则，通常为 *.bin,*.hex。",
            "远程地址：Git 远程仓库地址，用于 Pull、Push、验证远程和 .git 丢失后的恢复提示。",
            "保存按钮：保存当前配置到 .stm32_git_tool/app_config.json。",
            "取消按钮：放弃本次修改，不保存配置。",
        ]))
        layout.addLayout(form)
        layout.addLayout(buttons)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.project_type.currentTextChanged.connect(self.apply_template)

    def apply_template(self, name):
        template = get_template(name)
        self.include_dirs.setText(",".join(template.get("include_source_dirs", [])))
        self.exclude_dirs.setText(",".join(template.get("exclude_dirs", [])))
        self.exclude_patterns.setText(",".join(template.get("exclude_patterns", [])))
        self.firmware_patterns.setText(",".join(template.get("firmware_patterns", [])))

    def get_config(self):
        config = self.config.copy()
        config.update(
            {
                "firmware_dir": self.firmware_dir.text().strip(),
                "project_type": self.project_type.currentText(),
                "release_dir": self.release_dir.text().strip() or ".stm32_git_tool/releases",
                "include_source_dirs": self._split(self.include_dirs.text()),
                "exclude_dirs": self._split(self.exclude_dirs.text()),
                "exclude_patterns": self._split(self.exclude_patterns.text()),
                "firmware_patterns": self._split(self.firmware_patterns.text()),
                "remote": self.remote.text().strip(),
            }
        )
        return config

    @staticmethod
    def _split(text):
        return [item.strip() for item in text.split(",") if item.strip()]
