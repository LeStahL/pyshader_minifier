from typing import (
    Self,
    Optional,
    List,
    Tuple,
    Dict,
)
from enum import (
    IntEnum,
    auto,
)
from subprocess import (
    run,
    CompletedProcess,
)
from pathlib import Path
from parse import parse
from threading import Thread
from queue import Queue
from PyQt6.QtCore import (
    QObject,
    pyqtSignal,
    QVariant,
)
from time import sleep
from traceback import print_exc


class LinkerType(IntEnum):
    Unavailable = auto()
    Crinkler = auto()
    Cold = auto()


class Entropy(QObject):
    FPS = 10
    built: pyqtSignal = pyqtSignal(QVariant)
    stopped: pyqtSignal = pyqtSignal()

    def __init__(
        self: Self,
        buildCommand: Optional[List[str]] = None,
        home: Optional[Path] = None,
    ) -> None:
        super().__init__()

        self._buildCommand: Optional[List[str]] = buildCommand
        self._home: Path = home if home is not None else Path('.')
        
        self._versions: Dict[str, float] = {}

        self._thread: Thread = Thread(target=self._run)
        self._queue: Queue = Queue()
        self._running: bool = True
        self._reset: bool = False


    def start(self: Self) -> None:
        self._thread.start()

    def stop(self: Self) -> None:
        self._running = False

    def _run(self: Self) -> int:
        while self._running:
            if self._reset:
                while self._queue.qsize() != 0:
                    self._queue.get()
                self._versions = {}
                self._reset = False

            while self._queue.qsize() != 0:
                hash = self._queue.get()

                if self._buildCommand is not None:
                    try:
                        result: Optional[CompletedProcess] = run(
                            self._buildCommand,
                            cwd=self._home,
                            capture_output=True,
                        )

                        if result.returncode == 0:
                            data_size: Optional[float] = None
                            parsed: bool = False

                            # Attempt to parse Cold output format.
                            try:
                                lines: List[str] = list(filter(
                                    lambda line: "Entropy" in line.lstrip(),
                                    result.stderr.decode('utf-8').strip().splitlines(),
                                ))
                                [data_size, _, _] = parse(
                                    "\x1b[1m\x1b[32m==>\x1b[0m\x1b[1m Entropy: {} + {} = {}\x1b[0m",
                                    lines[0],
                                )
                                parsed = True
                            except:
                                pass

                            # Attempt to parse Crinkler output format.
                            lines: List[str] = list(filter(
                                lambda line: line.lstrip().startswith("Ideal compressed size of data:"),
                                result.stdout.decode('utf-8').strip().splitlines(),
                            ))
                            if len(lines) != 0:
                                [data_size] = parse(
                                    "Ideal compressed size of data: {}",
                                    lines[0].lstrip().rstrip(),
                                )
                                parsed = True

                            if not parsed:
                                print("Could not parse build output:")
                                print(result.stdout.decode('utf-8').strip())
                                print(result.stderr.decode('utf-8').strip())

                            self._versions[hash] = data_size
                    except:
                        print_exc()
                        self._versions[hash] = 'Errored'
                    self.built.emit(self)

            sleep(1./Entropy.FPS)

        self.stopped.emit()

        return 0

    def determineEntropy(self: Self, sha256: str) -> Optional[Tuple[int, int, int]]:
        self._queue.put(sha256)

    def reset(self: Self) -> None:
        self._reset = True
