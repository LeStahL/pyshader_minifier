from PyQt6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
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
    Optional,
)
from shader_minifier.watcher import Watcher
from shader_minifier.scheduler import Scheduler
from shader_minifier.entropy import Entropy

class VersionModel(QAbstractTableModel):
    HorizontalHeaders = ['SHA256', 'size', 'ratio', 'entropy']

    def __init__(
        self: Self,
        parent: Optional[QObject] = None,
     ) -> None:
        super().__init__(parent)
        
        self._watcher: Optional[Watcher] = None
        self._scheduler: Optional[Scheduler] = None
        self._entropy: Optional[Entropy] = None

    def updateWatcher(self: Self, watcher: Watcher) -> None:
        self.beginResetModel()
        self._watcher = watcher
        self.endResetModel()

    def updateScheduler(self: Self, scheduler: Scheduler) -> None:
        self.beginResetModel()
        self._scheduler = scheduler
        self.endResetModel()

    def updateEntropy(self: Self, entropy: Entropy) -> None:
        self.beginResetModel()
        self._entropy = entropy
        self.endResetModel()

    def rowCount(
        self: Self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        return len(self._watcher._history.values()) if self._watcher is not None else 0
    
    def columnCount(
        self: Self,
        parent: QModelIndex = QModelIndex(),
    ) -> int:
        return len(VersionModel.HorizontalHeaders)
    
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

        if role == Qt.ItemDataRole.DisplayRole:
            hash: str = list(self._watcher._history.values())[index.row()]
            if index.column() == 0:
                # Hash
                return hash
            if index.column() == 1:
                # File size
                if hash not in self._scheduler._versions.keys():
                    return 'Pending'
                
                minified: Any = self._scheduler._versions[hash]
                if type(minified) == str:
                    return len(minified) 
                
                return 'Error'
            if index.column() == 2:
                # Compression ratio
                if hash not in self._scheduler._versions.keys():
                    return 'Pending'
                
                unminified: str = self._watcher._versions[hash]
                minified: Any = self._scheduler._versions[hash]
                if type(minified) == str:
                    return len(minified) / len(unminified)
                
                return 'Error'
            if index.column() == 3:
                if self._entropy is None:
                    return 'Unavailable'
                
                if hash not in self._entropy._versions.keys():
                    return 'Unavailable'
                
                return self._entropy._versions[hash]

        if role == Qt.ItemDataRole.FontRole:
            hash: str = list(self._watcher._history.values())[index.row()]

            if hash == self._watcher.latestHash:
                font: QFont = QFont()
                font.setBold(True)
                return font

        if role == Qt.ItemDataRole.ForegroundRole:
            hash: str = list(self._watcher._history.values())[index.row()]
            if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                # Pending
                if hash not in self._scheduler._versions.keys():
                    return QColor(119, 119, 119)
                
                # Error
                minified: Any = self._scheduler._versions[hash]
                if type(minified) != str:
                    return QColor(255, 173, 51)
                
                # Ok
                return QColor(76, 255, 76)
            
        if role == Qt.ItemDataRole.BackgroundRole:
            hash: str = list(self._watcher._history.values())[index.row()]
            if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                # Pending
                if hash not in self._scheduler._versions.keys():
                    return QColor(60, 60, 60)

                # Error
                minified: Any = self._scheduler._versions[hash]
                if type(minified) != str:
                    return QColor(74, 35, 36)

                # Ok
                return QColor(31, 54, 35)
            else:
                # Pending
                if hash not in self._scheduler._versions.keys():
                    return QColor(255, 251, 231)

                # Error
                minified: Any = self._scheduler._versions[hash]
                if type(minified) != str:
                    return QColor(251, 233, 235)

                # Ok
                return QColor(236, 253, 240)

    def headerData(
        self: Self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return VersionModel.HorizontalHeaders[section]
            return list(self._watcher._history.keys())[section].strftime("%H:%M:%S")
