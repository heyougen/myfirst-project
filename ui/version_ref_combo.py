from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QComboBox, QCompleter

try:
    from core.i18n import tr
except ModuleNotFoundError:
    from stm32_git_release_tool.core.i18n import tr


class VersionRefComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_model = QStandardItemModel(self)
        self.setModel(self.source_model)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.lineEdit().setClearButtonEnabled(True)
        self.lineEdit().setPlaceholderText(tr("搜索版本号、日期或修改说明"))
        self.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.completer().setFilterMode(Qt.MatchContains)
        self.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.completer().activated[str].connect(self._select_label)

    def set_refs(self, refs):
        current_ref = self.current_ref()
        self.blockSignals(True)
        self.source_model.clear()
        for ref in refs:
            item = QStandardItem(ref["label"])
            item.setData(ref["ref"], Qt.UserRole)
            item.setData(ref["kind"], Qt.UserRole + 1)
            self.source_model.appendRow(item)
        self.blockSignals(False)
        if current_ref and self.set_current_ref(current_ref):
            return
        if self.count() > 0:
            self.setCurrentIndex(0)

    def current_ref(self):
        if self.currentIndex() < 0:
            return ""
        model_index = self.model().index(self.currentIndex(), 0)
        selected_label = str(model_index.data(Qt.DisplayRole) or "")
        if self.lineEdit().text() != selected_label:
            return ""
        ref = self.currentData(Qt.UserRole)
        return str(ref).strip() if ref else ""

    def current_kind(self):
        kind = self.currentData(Qt.UserRole + 1)
        return str(kind).strip() if kind else ""

    def set_current_ref(self, ref):
        for row in range(self.source_model.rowCount()):
            item = self.source_model.item(row)
            if str(item.data(Qt.UserRole)) == str(ref):
                self.setCurrentIndex(row)
                return True
        return False

    def _select_label(self, label):
        index = self.findText(label, Qt.MatchExactly)
        if index >= 0:
            self.setCurrentIndex(index)

    def showPopup(self):
        # The combo always keeps its full source model, so clearing a search can
        # never leave the arrow pointing at an empty filtered proxy model.
        super().showPopup()
