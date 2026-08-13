"""FRU field editor list model for QML."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt, pyqtSignal, pyqtSlot

from frutool.config import FRU_FIELDS


@dataclass
class _FruFieldRow:
    name: str
    area: str
    idx: str
    group: str
    value: str = ""
    hint: str = ""


class FruFieldModel(QAbstractListModel):
    NameRole = Qt.ItemDataRole.UserRole + 1
    AreaRole = Qt.ItemDataRole.UserRole + 2
    IdxRole = Qt.ItemDataRole.UserRole + 3
    GroupRole = Qt.ItemDataRole.UserRole + 4
    ValueRole = Qt.ItemDataRole.UserRole + 5
    HintRole = Qt.ItemDataRole.UserRole + 6

    valueChanged = pyqtSignal(int)
    hintsChanged = pyqtSignal()

    def __init__(self, parent: Optional[object] = None):
        super().__init__(parent)
        self._rows = [_FruFieldRow(name, area, idx, group) for name, area, idx, group in FRU_FIELDS]

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.AreaRole: b"area",
            self.IdxRole: b"idx",
            self.GroupRole: b"group",
            self.ValueRole: b"value",
            self.HintRole: b"hint",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._rows):
            return None
        field = self._rows[row]
        if role == self.NameRole:
            return field.name
        if role == self.AreaRole:
            return field.area
        if role == self.IdxRole:
            return field.idx
        if role == self.GroupRole:
            return field.group
        if role == self.ValueRole:
            return field.value
        if role == self.HintRole:
            return field.hint
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or role != self.ValueRole:
            return False
        row = index.row()
        if row < 0 or row >= len(self._rows):
            return False
        text = str(value)
        if self._rows[row].value == text:
            return True
        self._rows[row].value = text
        self.dataChanged.emit(index, index, [self.ValueRole])
        self.valueChanged.emit(row)
        return True

    @pyqtSlot(int, str)
    def setValueAt(self, row: int, value: str) -> None:
        self.setData(self.index(row), value, self.ValueRole)

    @pyqtSlot(str, str, str)
    def setValueByKey(self, area: str, idx: str, value: str) -> None:
        for i, field in enumerate(self._rows):
            if field.area == area and field.idx == idx:
                self.setValueAt(i, value)
                return

    def nonEmptyFields(self) -> list[tuple[str, str, str]]:
        return [(f.area, f.idx, f.value.strip()) for f in self._rows if f.value.strip()]

    @pyqtSlot(int, str)
    def setHintAt(self, row: int, hint: str) -> None:
        if row < 0 or row >= len(self._rows):
            return
        text = str(hint)
        if self._rows[row].hint == text:
            return
        self._rows[row].hint = text
        index = self.index(row)
        self.dataChanged.emit(index, index, [self.HintRole])

    @pyqtSlot("QVariantMap")
    def setHints(self, values: dict) -> None:
        changed = False
        for i, field in enumerate(self._rows):
            new_hint = str(values.get(field.name, "") or "")
            if self._rows[i].hint != new_hint:
                self.setHintAt(i, new_hint)
                changed = True
        if changed:
            self.hintsChanged.emit()

    @pyqtSlot()
    def clearAllValues(self) -> None:
        for i in range(len(self._rows)):
            if self._rows[i].value:
                self.setValueAt(i, "")

    @pyqtSlot()
    def clearAllHints(self) -> None:
        changed = False
        for i, field in enumerate(self._rows):
            if field.hint:
                self.setHintAt(i, "")
                changed = True
        if changed:
            self.hintsChanged.emit()

    def hint_for_name(self, name: str) -> str:
        for field in self._rows:
            if field.name == name:
                return field.hint
        return ""
