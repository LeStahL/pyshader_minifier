from typing import (
    Self,
    Dict,
    Any,
    Optional,
)
from pathlib import Path
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    QVariant,
    QFileSystemWatcher,
)
from hashlib import sha256
from datetime import datetime
from json import dumps
from threading import Thread
from queue import Queue
from time import sleep


class Watcher(QObject):
    FPS = 10
    
    fileChanged: pyqtSignal = pyqtSignal(QVariant)
    fileLoaded: pyqtSignal = pyqtSignal(str)
    historyExported: pyqtSignal = pyqtSignal(str)
    stopped: pyqtSignal = pyqtSignal()
    resetted: pyqtSignal = pyqtSignal()

    def __init__(self: Self) -> None:
        super().__init__()

        self._path: Optional[Path] = None
        self._versions: Dict[str, str] = {}
        self._history: Dict[datetime, str] = {}
        self._latestHash: Optional[str] = None

        self._watcher: QFileSystemWatcher = QFileSystemWatcher()
        
        self._queue: Queue = Queue()
        self._thread: Thread = Thread(target=self._run)
        
        self._running: bool = True
        self._reset: bool = False
        
    def start(self: Self) -> None:
        self._thread.start()
        
    def stop(self: Self) -> None:
        self._running = False
        
    def _run(self: Self) -> int:
        while self._running:
            if self._watcher is not None and self._path is not None and len(self._watcher.files()) == 0:
                print("We lost our directory (wtf, qt, no signal?!). Reclaiming.")
                self._watcher.addPath(str(self._path))
                self.updateFile()

            if self._reset:
                while self._queue.qsize() != 0:
                    self._queue.get()
                self._versions = {}
                self._latestHash = None
                self._reset = False
                self.resetted.emit()

            while self._queue.qsize() != 0:
                self._queue.get()

                print("Updating.")
                if self._path is None:
                    break

                data: bytes = self._path.read_bytes()
                hash: str = sha256(data).digest().hex()
                source: str = data.decode('utf-8')

                if not self._latestHash == hash:
                    if hash not in self._versions.keys():
                        self._versions[hash] = source

                    self._history[datetime.now()] = hash
                    self._latestHash = hash
                    self.fileChanged.emit(self)
                else:
                    print("Ignored update.")

            sleep(1 / Watcher.FPS)

        self.stopped.emit()
        return 0

    def watchFile(self: Self, path: Any) -> None:
        if self._path is not None:
            self._watcher.removePath(str(self._path))

        self._versions: Dict[str, str] = {}
        self._history: Dict[datetime, str] = {}
        self._latestHash: Optional[str] = None
        self._path = Path(path)

        self._watcher.addPath(str(self._path))
        self._watcher.fileChanged.connect(self.updateFile)
        self.fileLoaded.emit(str(self._path))

    def updateFile(self: Self) -> None:
        self._queue.put(None)

    def saveHistory(self: Self, filename: Any) -> None:
        Path(filename).write_text(dumps(
            {
                "versions": self._versions,
                "history": list(map(
                    lambda _datetime: {
                        "datetime": _datetime.isoformat(),
                        "sha256": self._history[_datetime],
                    },
                    self._history,
                )),
            },
            indent=4,
        ))
        self.historyExported.emit(filename)

    @property
    def latestHash(self: Self) -> Optional[str]:
        return self._latestHash

    def reset(self: Self) -> None:
        self._reset = True
