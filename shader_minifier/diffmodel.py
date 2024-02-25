from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    QSize,
    QVariant,
)
from PyQt6.QtGui import (
    QFont,
    QColor,
)
from PyQt6.QtWidgets import (
    QApplication,
)
from typing import (
    Any,
    Self,
    List,
    Optional,
)
from shader_minifier.watcher import Watcher
from shader_minifier.scheduler import Scheduler
from difflib import Differ


class DiffModel(QAbstractTableModel):
    HorizontalHeaders = ["Diff"]

    def __init__(
        self: Self,
        parent: Optional[QObject] = None,
     ) -> None:

        super().__init__(parent)
        
        QApplication.styleHints().colorSchemeChanged.connect(self._updateColors)

        self._watcher: Optional[Watcher] = None
        self._scheduler: Optional[Scheduler] = None
        self._referenceSHA: Optional[str] = None
        self._diff: Optional[List[str]] = None
        self._filteredDiff: Optional[List[str]] = None
        self._differ: Differ = Differ()
        self._rowHeaders: List[str] = []
        self._colors: List[QColor] = []
        self._font: QFont = QFont("Monospace")
        self._font.setStyleHint(QFont.StyleHint.TypeWriter)
        self._minified: bool = True

    def updateWatcher(self: Self, watcher: Watcher) -> None:
        self.beginResetModel()
        self._watcher = watcher
        self._determineDiff()
        self.endResetModel()

    def updateScheduler(self: Self, scheduler: Scheduler) -> None:
        self.beginResetModel()
        self._scheduler = scheduler
        self._determineDiff()
        self.endResetModel()

    def updateReferenceSHA(self: Self, hash: str) -> None:
        self.beginResetModel()
        self._referenceSHA = hash
        self._determineDiff()
        self.endResetModel()

    def updateMinified(self: Self, minified: bool) -> None:
        self.beginResetModel()
        self._minified = minified
        self._determineDiff()
        self.endResetModel()

    def _updateColors(self: Self) -> None:
        self.beginResetModel()
        self._determineDiff()
        self.endResetModel()

    def _determineDiff(self: Self) -> None:
        if True in [
            self._referenceSHA is None,
            self._scheduler is None,
            self._watcher is None,
        ] or False in [
            self._referenceSHA in self._scheduler._versions,
            self._watcher.latestHash in self._scheduler._versions,
        ]:
            return
        
        # TODO: Can we make this code block more maintainable?
        if self._minified:
            if type(self._scheduler._versions[self._referenceSHA]) != str:
                self._original = ["Reference ref errored."]
                self._new = self._scheduler._versions[self._referenceSHA].args[0].strip().splitlines()
            elif type(self._scheduler._versions[self._watcher.latestHash]) != str:
                self._original = ["Latest ref errored."]
                self._new = self._scheduler._versions[self._watcher.latestHash].args[0].strip().splitlines()
            else:
                self._original = self._scheduler._versions[self._referenceSHA].splitlines()
                self._new = self._scheduler._versions[self._watcher.latestHash].splitlines()
        else:
            if type(self._scheduler._versions[self._referenceSHA]) != str:
                self._original = ["Reference ref errored."]
                self._new = self._scheduler._versions[self._referenceSHA].args[0].strip().splitlines()
            elif type(self._scheduler._versions[self._watcher.latestHash]) != str:
                self._original = ["Latest ref errored."]
                self._new = self._scheduler._versions[self._watcher.latestHash].args[0].strip().splitlines()
            else:
                self._original = self._watcher._versions[self._referenceSHA].splitlines()
                self._new = self._watcher._versions[self._watcher.latestHash].splitlines()

        self._diff = list(self._differ.compare(
            self._original,
            self._new,
        ))
        self._filteredDiff = list(filter(
            lambda line: not line.startswith(' '), 
            self._diff,
        ))
        def mapping(lineInDiff: str) -> str:
            if lineInDiff.startswith('-'):
                return "R:{}".format(
                self._original.index(lineInDiff[2:]),
            )
            elif lineInDiff.startswith('+'):
                return "L:{}".format(
                    self._new.index(lineInDiff[2:]),
                )
            return ""
        self._rowHeaders = list(map(
            mapping,
            self._filteredDiff,
        ))
        def mapping(line: str) -> QColor:
            if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                if line.startswith('-'):
                    return QColor(74, 35, 36)
                elif line.startswith('+'):
                    return QColor(31, 54, 35)
                else:
                    return
            else:
                if line.startswith('-'):
                    return QColor(251, 233, 235)
                elif line.startswith('+'):
                    return QColor(236, 253, 240)
                else:
                    return
        self._colors = list(map(
            mapping,
            self._filteredDiff,
        ))
            

    def rowCount(
        self: Self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        return len(self._filteredDiff) if self._filteredDiff is not None else 0
    
    def columnCount(
        self: Self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        return len(DiffModel.HorizontalHeaders)
    
    def data(
        self: Self,
        index: QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid():
            return
        
        if self._watcher is None:
            return
        
        if self._scheduler is None:
            return
        
        if self._filteredDiff is None:
            return

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return self._filteredDiff[index.row()]
            else:
                return

        elif role == Qt.ItemDataRole.FontRole:
            return self._font

        elif role == Qt.ItemDataRole.BackgroundRole:
            return self._colors[index.row()]

    def headerData(
        self: Self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if self._filteredDiff is None:
            return

        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return DiffModel.HorizontalHeaders[section]

            return self._rowHeaders[section]
