from PyQt5.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout


def make_help_box(title: str, steps: list[str]) -> QPushButton:
    button = QPushButton("操作说明")
    button.setToolTip(title)
    button.clicked.connect(lambda: show_help_dialog(title, steps, button))
    return button


def show_help_dialog(title: str, steps: list[str], parent=None) -> None:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(780, 620)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setLineWrapMode(QTextEdit.WidgetWidth)
    text.setPlainText(format_help_text(steps))

    close_button = QPushButton("关闭")
    close_button.clicked.connect(dialog.accept)

    layout = QVBoxLayout(dialog)
    layout.addWidget(text)
    layout.addWidget(close_button)
    dialog.exec_()


def format_help_text(steps: list[str]) -> str:
    return "\n\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
