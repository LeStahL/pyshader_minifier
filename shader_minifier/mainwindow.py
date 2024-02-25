from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QSettings,
    QDir,
    QFileInfo,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QVariant,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QMessageBox,
    QFileDialog,
    QTableView,
    QHeaderView,
    QComboBox,
    QToolBar,
)
from PyQt6.QtGui import (
    QAction,
    QCloseEvent,
    QIcon,
)
from PyQt6.uic import loadUi
from typing import (
    Self,
    Optional,
    List,
)
from importlib.resources import files
from importlib.abc import Traversable
import shader_minifier
from shader_minifier.version import Version
from shader_minifier.watcher import Watcher
from shader_minifier.versionmodel import VersionModel
from shader_minifier.scheduler import Scheduler
from shader_minifier.diffmodel import DiffModel
from shader_minifier.entropy import Entropy
from shader_minifier.minifier import MinifierVersion


class MainWindow(QMainWindow):
    UiFile: Traversable = files(shader_minifier) / 'mainwindow.ui'
    IconFile: Traversable = files(shader_minifier) / 'team210.ico'

    SupportedExportFileTypes: str = "All Supported Files (*.json);;JSON files (*.json)"
    SupportedFileTypes: str = "All Supported Files (*.glsl *.frag *.vert *.geom *.tess *.hlsl);;Shader files (*.glsl *.frag *.vert *.geom *.tess *.hlsl)"

    quitRequested: pyqtSignal = pyqtSignal()
    fileChangeRequested: pyqtSignal = pyqtSignal(str)
    exportRequested: pyqtSignal = pyqtSignal(str)
    # hash, size, entropy
    commitRequested: pyqtSignal = pyqtSignal(str, int, QVariant)
    minifierVersionRequested: pyqtSignal = pyqtSignal(str)

    def __init__(
        self: Self,
        parent: Optional[QWidget] = None,
        flags: Qt.WindowType = Qt.WindowType.Window,
    ) -> None:
        super().__init__(parent, flags)

        loadUi(MainWindow.UiFile, self)
        self.setWindowIcon(QIcon(str(MainWindow.IconFile)))

        self.actionQuit: QAction
        self.actionQuit.triggered.connect(self.quitRequested.emit)

        self.actionExport_History: QAction
        self.actionExport_History.triggered.connect(self.exportHistory)

        self.actionOpen: QAction
        self.actionOpen.triggered.connect(self.open)

        self.actionAbout: QAction
        self.actionAbout.triggered.connect(lambda: QMessageBox.about(
            self,
            "About pyshader_minifier...",
            "pyshader_minifier {} is (c) 2024 Alexander Kraus <nr4@z10.info>.".format(
                Version().describe(),
            ),
        ))

        self.actionAbout_Qt: QAction
        self.actionAbout_Qt.triggered.connect(lambda: QMessageBox.aboutQt(
            self,
            "About Qt...",
        ))

        self._versionModel: VersionModel = VersionModel(self)
        
        self.versionView: QTableView
        self.versionView.setModel(self._versionModel)
        self.versionView.selectionModel().selectionChanged.connect(self.versionSelectionChanged)

        self._diffModel: DiffModel = DiffModel(self)

        self.diffView: QTableView
        self.diffView.setModel(self._diffModel)
        self.diffView.setWordWrap(False)
        self.diffView.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.diffView.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)

        self.actionCommit: QAction
        self.actionCommit.triggered.connect(self.commit)

        self.actionMinified: QAction
        self.actionMinified.triggered.connect(self.minified)

        self.minifierComboBox: QComboBox = QComboBox(self)
        for minifierVersion in MinifierVersion:
            if minifierVersion != MinifierVersion.unavailable:
                self.minifierComboBox.addItem(minifierVersion.name)
        self.minifierComboBox.currentTextChanged.connect(self.minifierSelected)

        self.toolBar: QToolBar
        self.toolBar.addWidget(self.minifierComboBox)

    def minifierSelected(self: Self) -> None:
        self.minifierVersionRequested.emit(self.minifierComboBox.currentText())

    def open(self: Self) -> None:
        settings = QSettings()
        filename, _ = QFileDialog.getOpenFileName(
            self,
            'Open shader...',
            settings.value("open_path", QDir.homePath()),
            MainWindow.SupportedFileTypes,
        )
        
        if filename == "":
            return

        file_info = QFileInfo(filename)
        settings.setValue("open_path", file_info.absoluteDir().absolutePath())

        self.statusBar().showMessage("Opening file {}.".format(filename))
        self.fileChangeRequested.emit(filename)

    def fileChanged(self: Self, filename: str) -> None:
        self.statusBar().clearMessage()
        self.setWindowTitle("PyShaderMinifier by Team210 - {}.".format(filename))
        self.statusBar().showMessage("Finished opening file {}.".format(filename), 2000)

    def exportHistory(self: Self) -> None:
        settings: QSettings = QSettings()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            'Export history as...',
            settings.value("save_path", QDir.homePath()),
            MainWindow.SupportedExportFileTypes,
        )

        if filename == "":
            return

        file_info = QFileInfo(filename)
        settings.setValue("save_path", file_info.absoluteDir().absolutePath())

        self.statusBar().showMessage("Exporting history to {}.".format(filename))
        self.exportRequested.emit(filename)

    def historyExported(self: Self, filename: str) -> None:
        self.statusBar().clearMessage()
        self.statusBar().showMessage("Finished exporting history to {}.".format(filename), 2000)

    def updateModelsFromWatcher(self: Self, watcher: Watcher) -> None:
        self._versionModel.updateWatcher(watcher)
        self._diffModel.updateWatcher(watcher)
        self._updateSelection()
    
    def _updateSelection(self: Self) -> None:
        if self._diffModel._referenceSHA is None:
            return

        referenceHashes: List[QModelIndex] = self._versionModel.match(self._versionModel.index(0, 0), Qt.ItemDataRole.DisplayRole, self._diffModel._referenceSHA)
        if len(referenceHashes) > 0:
            self.versionView.selectionModel().select(referenceHashes[0], QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)
        
    def updateModelsFromScheduler(self: Self, scheduler: Scheduler) -> None:
        self._versionModel.updateScheduler(scheduler)
        self._diffModel.updateScheduler(scheduler)
        self._updateSelection()

    def updateModelsFromEntropy(self: Self, entropy: Entropy) -> None:
        self._versionModel.updateEntropy(entropy)
        self._updateSelection()

    def versionSelectionChanged(
        self: Self,
        selected: QItemSelection,
        _: QItemSelection,
    ) -> None:
        if len(selected.indexes()) < 1:
            return
        
        selectedSHA: str = self._versionModel.data(self._versionModel.index(selected.indexes()[0].row(), 0))
        self._diffModel.updateReferenceSHA(selectedSHA)

    def closeEvent(
        self: Self,
        _: Optional[QCloseEvent],
    ) -> None:
        self.quitRequested.emit()

    def commit(self: Self) -> None:
        if self._versionModel._watcher is None:
            return

        if self._versionModel._entropy is None:
            return

        self.commitRequested.emit(
            self._versionModel._watcher.latestHash,
            len(self._versionModel._watcher._versions[self._versionModel._watcher.latestHash]),
            QVariant(self._versionModel._entropy._versions[self._versionModel._watcher.latestHash] if self._versionModel._watcher.latestHash in self._versionModel._entropy._versions else QVariant('Errored'))
        )

    def minified(self: Self) -> None:
        self._diffModel.updateMinified(self.actionMinified.isChecked())
