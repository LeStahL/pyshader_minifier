from typing import (
    Self,
    Optional,
)
from pygit2 import (
    Repository,
    Oid,
)
from pathlib import Path
from queue import Queue
from threading import Thread
from time import sleep
from PyQt6.QtCore import (
    pyqtSignal,
    QVariant,
    QObject,
)
from traceback import print_exc


class VCS(QObject):
    GitRepositorySuffix: str = '.git'
    FPS: int = 10

    commited: pyqtSignal = pyqtSignal(QVariant)
    stopped: pyqtSignal = pyqtSignal()
    resetted: pyqtSignal = pyqtSignal()
    hasRepoChanged: pyqtSignal = pyqtSignal(bool)

    def __init__(
        self: Self,
        path: Optional[Path] = None,
    ) -> None:
        super().__init__()

        self._path: Path = Path(path) if path is not None else path

        self._queue: Queue = Queue()
        self._thread: Thread = Thread(target=self._run)
        self._running: bool = True

        self._latestHash: str = ""
        self._shader: Optional[Path] = None

        self._reset: bool = False
    
    @property
    def shader(self: Self) -> Optional[Path]:
        return self._shader
    
    @shader.setter
    def shader(self: Self, value: Path) -> None:
        self._shader = Path(value).absolute()

        path = Path(value).absolute()
        while path.parent != path:
            repoPath: Path = path / VCS.GitRepositorySuffix
            if(repoPath.exists()):
                self._path = path
                self._repository: Repository = Repository(str(path))
                break

            path = path.parent

        if path.parent == path:
            self._path = None

        self.hasRepoChanged.emit(self._path is not None)

    def changeShader(self: Self, value: Path) -> None:
        self.shader = value

    def start(self: Self) -> None:
        self._thread.start()

    def stop(self: Self) -> None:
        self._running = False

    def _run(self: Self) -> None:
        while self._running:
            if self._reset:
                while self._queue.qsize() != 0:
                    self._queue.get()
                self._latestHash = ""
                self._shader = ""
                self._reset = False
                self.resetted.emit()

            while self._queue.qsize() != 0:
                hash, size, entropy = self._queue.get()

                if not self._latestHash == hash:
                    try:
                        self._repository.index.add(self._shader.relative_to(self._path))
                        self._repository.index.write()

                        commit: Oid = self._repository.create_commit(
                            None,
                            self._repository.default_signature,
                            self._repository.default_signature,
                            """Crunched {shaderName} to {size} bytes using PyShaderMinifier.
    Shader file: {shader}
    New size: {size}
    New entropy: {entropy}
    """.format(
        shader=self._shader.relative_to(self._path),
        shaderName=self._shader.name if self._shader is not None else 'Unavailable',
        size=size,
        entropy=entropy,
    ),
                            self._repository.index.write_tree(),
                            [self._repository.head.target],
                        )
                        self._repository.head.set_target(commit)
                    except:
                        print("Error: Could not create commit.")
                        print_exc()
                else:
                    # A commit only makes sense if something has actually changed.
                    print("Warning: Ignoring attempted empty commit with identical hash.")

            sleep(1 / VCS.FPS)

    def createCommit(
        self: Self,
        hash: str,
        size: int,
        entropy: Optional[int] = None,
    ) -> None:
        self._queue.put((hash, size, entropy))

    def reset(self: Self) -> None:
        self._reset = True
