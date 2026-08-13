"""Network interface list model for QML."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt

from frutool.infrastructure.network import NetworkChoice


class NetworkListModel(QAbstractListModel):
    LabelRole = Qt.ItemDataRole.UserRole + 1
    AliasRole = Qt.ItemDataRole.UserRole + 2
    Ipv4Role = Qt.ItemDataRole.UserRole + 3
    IndexRole = Qt.ItemDataRole.UserRole + 4

    def __init__(self, parent: Optional[object] = None):
        super().__init__(parent)
        self._choices: list[NetworkChoice] = []

    def roleNames(self):
        return {
            self.LabelRole: b"label",
            self.AliasRole: b"alias",
            self.Ipv4Role: b"ipv4",
            self.IndexRole: b"index",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._choices)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._choices):
            return None
        choice = self._choices[row]
        if role == self.LabelRole:
            return choice.label
        if role == self.AliasRole:
            return choice.alias
        if role == self.Ipv4Role:
            return choice.ipv4
        if role == self.IndexRole:
            return row
        return None

    def choiceAt(self, index: int) -> Optional[NetworkChoice]:
        if 0 <= index < len(self._choices):
            return self._choices[index]
        return None

    def setChoices(self, choices: list[NetworkChoice]) -> None:
        self.beginResetModel()
        self._choices = list(choices)
        self.endResetModel()
