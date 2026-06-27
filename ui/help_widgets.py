from typing import List

from PyQt5.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout

try:
    from core.i18n import tr
except ModuleNotFoundError:
    from stm32_git_release_tool.core.i18n import tr


def make_help_box(title: str, steps: List[str]) -> QPushButton:
    button = QPushButton(tr("操作说明"))
    button.setToolTip(tr(title))
    button.clicked.connect(lambda: show_help_dialog(title, steps, button))
    return button


def show_help_dialog(title: str, steps: List[str], parent=None) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(tr(title))
    dialog.resize(780, 620)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setLineWrapMode(QTextEdit.WidgetWidth)
    text.setPlainText(format_help_text(steps))

    close_button = QPushButton(tr("关闭"))
    close_button.clicked.connect(dialog.accept)

    layout = QVBoxLayout(dialog)
    layout.addWidget(text)
    layout.addWidget(close_button)
    dialog.exec_()


def format_help_text(steps: List[str]) -> str:
    return "\n\n".join(f"{index}. {tr(step)}" for index, step in enumerate(steps, 1))
