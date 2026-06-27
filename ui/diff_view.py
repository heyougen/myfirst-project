import html
import re

from PyQt5.QtWidgets import QHBoxLayout, QListWidget, QTextEdit, QWidget


class DiffView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sections = []
        self.file_list = QListWidget()
        self.file_list.setFixedWidth(300)
        self.file_list.setStyleSheet(
            """
            QListWidget {
                outline: 0;
                border: 1px solid #d2d2d7;
                border-radius: 8px;
                background: #ffffff;
                font-size: 12px;
            }
            QListWidget::item {
                border: 0;
                padding: 5px 8px;
                min-height: 22px;
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
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QTextEdit.NoWrap)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.file_list)
        layout.addWidget(self.text, 1)

        self.file_list.currentRowChanged.connect(self._show_section)

    def set_loading(self, message="正在加载代码差异..."):
        self.sections = []
        self.file_list.clear()
        self.text.setPlainText(message)

    def set_plain(self, message):
        self.sections = []
        self.file_list.clear()
        self.text.setPlainText(message)

    def set_diff(self, diff_text):
        self.sections = split_diff_sections(diff_text)
        self.file_list.clear()
        for section in self.sections:
            self.file_list.addItem(section["file"])
        if self.sections:
            self.file_list.setCurrentRow(0)
        else:
            self.text.setHtml(render_diff_html(diff_text))

    def _show_section(self, row):
        if 0 <= row < len(self.sections):
            self.text.setHtml(render_diff_html(self.sections[row]["text"]))


def split_diff_sections(diff_text):
    sections = []
    current_file = ""
    current_lines = []

    def flush():
        if current_lines:
            sections.append(
                {
                    "file": current_file or "Diff",
                    "text": "\n".join(current_lines),
                }
            )

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            flush()
            current_lines = [line]
            current_file = extract_file_from_diff_header(line)
            continue
        if not current_lines and (line.startswith("commit ") or line.startswith("Author:") or line.startswith("Date:")):
            current_lines = [line]
            current_file = "提交信息"
            continue
        if current_lines:
            current_lines.append(line)
        else:
            current_lines = [line]
            current_file = "Diff"

    flush()
    if len(sections) > 1 and sections[0]["file"] == "提交信息":
        meta = sections.pop(0)
        if sections:
            sections[0]["text"] = meta["text"] + "\n" + sections[0]["text"]
    return sections


def extract_file_from_diff_header(line):
    match = re.match(r"diff --git a/(.*?) b/(.*)", line)
    if match:
        return match.group(2)
    return line.replace("diff --git ", "").strip() or "Diff"


def extract_diff_files(diff_text):
    return [section["file"] for section in split_diff_sections(diff_text)]


def render_diff_html(diff_text):
    rows = []
    old_line = None
    new_line = None

    for raw in diff_text.splitlines():
        old_no = ""
        new_no = ""
        line_text = raw
        kind = "normal"

        hunk = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(2))
            kind = "hunk"
        elif raw.startswith("diff --git ") or raw.startswith("commit "):
            kind = "file"
        elif raw.startswith("index ") or raw.startswith("--- ") or raw.startswith("+++ ") or raw.startswith("Author:") or raw.startswith("Date:"):
            kind = "meta"
        elif raw.startswith("+") and not raw.startswith("+++"):
            kind = "add"
            new_no = str(new_line) if new_line is not None else ""
            if new_line is not None:
                new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            kind = "del"
            old_no = str(old_line) if old_line is not None else ""
            if old_line is not None:
                old_line += 1
        else:
            if old_line is not None and new_line is not None and not raw.startswith("\\"):
                old_no = str(old_line)
                new_no = str(new_line)
                old_line += 1
                new_line += 1

        rows.append(render_row(old_no, new_no, line_text, kind))

    if not rows:
        rows.append('<tr><td colspan="3" style="padding:12px;color:#6e6e73;">没有代码差异。</td></tr>')

    return (
        '<html><body style="margin:0;background:#ffffff;">'
        '<table cellspacing="0" cellpadding="0" style="width:100%; '
        'font-family:Consolas, Cascadia Mono, monospace; font-size:12px;">'
        '<tr style="background:#f2f2f7;color:#6e6e73;">'
        '<th style="width:54px;text-align:right;padding:3px 8px;">旧行</th>'
        '<th style="width:54px;text-align:right;padding:3px 8px;">新行</th>'
        '<th style="text-align:left;padding:3px 8px;">代码差异</th>'
        '</tr>'
        + "\n".join(rows)
        + "</table></body></html>"
    )


def render_row(old_no, new_no, text, kind):
    styles = {
        "normal": ("#ffffff", "#1d1d1f", "400"),
        "file": ("#e8f0fe", "#0645ad", "700"),
        "meta": ("#f2f2f7", "#424245", "600"),
        "hunk": ("#fff4d6", "#8a5a00", "700"),
        "add": ("#e8f7ed", "#116329", "400"),
        "del": ("#fde8e8", "#b42318", "400"),
    }
    bg, color, weight = styles.get(kind, styles["normal"])
    safe_text = html.escape(text) or " "
    return (
        f'<tr style="background:{bg}; color:{color}; font-weight:{weight};">'
        f'<td style="width:54px;text-align:right;color:#8a8a8e;padding:1px 8px;border-right:1px solid #e5e5ea;">{old_no}</td>'
        f'<td style="width:54px;text-align:right;color:#8a8a8e;padding:1px 8px;border-right:1px solid #e5e5ea;">{new_no}</td>'
        f'<td style="white-space:pre;padding:1px 8px;">{safe_text}</td>'
        f"</tr>"
    )
