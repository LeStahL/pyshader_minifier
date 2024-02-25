from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    QVariant,
)
from typing import (
    Self,
    Dict,
    Optional,
)
from threading import Thread
from queue import Queue
from time import sleep
from shader_minifier.minifier import (
    MinifierVersion,
    shader_minifier,
    ObtainmentStrategy,
    ShaderMinifierError,
    ValidationError,
)


class Scheduler(QObject):
    FPS = 10

    # Hash, minified source
    minified: pyqtSignal = pyqtSignal(str, str)
    versionsUpdated: pyqtSignal = pyqtSignal(QVariant)

    # Hash, error text
    errored: pyqtSignal = pyqtSignal(str, QVariant)
    stopped: pyqtSignal = pyqtSignal()
    minifiersObtained: pyqtSignal = pyqtSignal()

    def __init__(self: Self) -> None:
        super().__init__()

        self._thread: Thread = Thread(target=self._run)
        self._queue: Queue = Queue()
        self._running: bool = True
        self._reset: bool = False
        self._minifiers: Dict[MinifierVersion, shader_minifier] = {}
        self._selectedVersion: MinifierVersion = MinifierVersion.v1_3_6

        self._versions: Dict[str, str] = {}

    def start(self: Self) -> None:
        self._thread.start()

    def minifyShader(self: Self, hash: str, source: str) -> None:
        self._queue.put((hash, source))

    def selectMinifierVersion(self: Self, version: MinifierVersion) -> None:
        self._selectedVersion = version

    def stop(self: Self) -> None:
        self._running = False

    def _load(self: Self, version: MinifierVersion) -> int:
        self._minifiers[version] = shader_minifier(version, ObtainmentStrategy.Download)
        return 0

    def _run(self: Self) -> int:
        threads: Dict[MinifierVersion, Thread] = {}

        for version in MinifierVersion:
            if version != MinifierVersion.unavailable:
                threads[version] = Thread(target=self._load, args=[version])
                threads[version].start()

        for version in MinifierVersion:
            if version != MinifierVersion.unavailable:
                threads[version].join()

        self.minifiersObtained.emit()

        while self._running:
            if self._reset:
                while self._queue.qsize() != 0:
                    self._queue.get()
                self._versions = {}
                self._reset = False
                self.versionsUpdated.emit(self)

            while self._queue.qsize() != 0:
                hash, source = self._queue.get()
                result: Optional[str] = None
                try:
                    result = self._minifiers[self._selectedVersion].minify(source)
                    self.minified.emit(hash, result)
                except ShaderMinifierError as error:
                    result = error
                    self.errored.emit(hash, error)
                except ValidationError as error:
                    result = error
                    self.errored.emit(hash, error)
                self._versions[hash] = result
                self.versionsUpdated.emit(self)
                
            sleep(1. / Scheduler.FPS)

        self.stopped.emit()

        return 0

    def reset(self: Self) -> None:
        self._reset = True

    def selectMinifier(self: Self, version: str) -> None:
        self._selectedVersion = MinifierVersion[version]
