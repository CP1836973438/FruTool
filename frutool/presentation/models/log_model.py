"""Append-only log line model for QML ListViews."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt, pyqtProperty, pyqtSignal, pyqtSlot

from frutool.theme.tokens import log_color, log_prefix


class LogLineModel(QAbstractListModel):
    """Append-only log lines with optional tab filter for QML ListViews."""

    LevelRole = Qt.ItemDataRole.UserRole + 1
    TextRole = Qt.ItemDataRole.UserRole + 2
    TimestampRole = Qt.ItemDataRole.UserRole + 3
    ColorRole = Qt.ItemDataRole.UserRole + 4
    TabRole = Qt.ItemDataRole.UserRole + 5
    FormattedRole = Qt.ItemDataRole.UserRole + 6

    tabFilterChanged = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._lines: list[dict] = []
        self._tab_filter = "all"
        self._theme_key = "dark"
        self._visible_indices: list[int] = []

    def roleNames(self):
        return {
            self.LevelRole: b"level",
            self.TextRole: b"text",
            self.TimestampRole: b"timestamp",
            self.ColorRole: b"color",
            self.TabRole: b"tab",
            self.FormattedRole: b"formatted",
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._visible_indices)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._visible_indices):
            return None
        entry = self._lines[self._visible_indices[row]]
        if role == self.LevelRole:
            return entry["level"]
        if role == self.TextRole:
            return entry["text"]
        if role == self.TimestampRole:
            return entry["timestamp"]
        if role == self.ColorRole:
            return entry["color"]
        if role == self.TabRole:
            return entry["tab"]
        if role == self.FormattedRole:
            return entry.get("formatted") or f"[{entry['timestamp']}] {entry['text']}"
        return None

    @pyqtProperty(str, notify=tabFilterChanged)
    def tabFilter(self) -> str:
        return self._tab_filter

    @tabFilter.setter
    def tabFilter(self, tab: str) -> None:
        if tab == self._tab_filter:
            return
        self._tab_filter = tab
        self.beginResetModel()
        self._rebuild_visible()
        self.endResetModel()
        self.tabFilterChanged.emit()

    def setThemeKey(self, theme_key: str) -> None:
        if theme_key == self._theme_key:
            return
        self._theme_key = theme_key
        for entry in self._lines:
            entry["color"] = log_color(theme_key, entry["level"])
            ts = entry.get("timestamp", "")
            entry["formatted"] = f"[{ts}] {log_prefix(entry['level'])} {entry['text']}"
        if self._lines:
            top = min(len(self._lines) - 1, self.rowCount() - 1)
            if top >= 0:
                self.dataChanged.emit(self.index(0), self.index(top), [self.ColorRole])

    def append(self, level: str, text: str, timestamp: str, tab: str) -> None:
        prefix = log_prefix(level)
        entry = {
            "level": level,
            "text": text,
            "timestamp": timestamp,
            "color": log_color(self._theme_key, level),
            "tab": tab,
            "formatted": f"[{timestamp}] {prefix} {text}",
        }
        self._lines.append(entry)
        if tab != self._tab_filter:
            return
        row = len(self._visible_indices)
        self.beginInsertRows(QModelIndex(), row, row)
        self._visible_indices.append(len(self._lines) - 1)
        self.endInsertRows()

    @pyqtSlot(str)
    def clearTab(self, tab: str) -> None:
        if tab == "all":
            self.beginResetModel()
            self._lines.clear()
            self._visible_indices.clear()
            self.endResetModel()
            return
        self.beginResetModel()
        self._lines = [entry for entry in self._lines if entry["tab"] != tab]
        self._rebuild_visible()
        self.endResetModel()

    def _rebuild_visible(self) -> None:
        self._visible_indices = [
            i for i, entry in enumerate(self._lines) if entry["tab"] == self._tab_filter
        ]
