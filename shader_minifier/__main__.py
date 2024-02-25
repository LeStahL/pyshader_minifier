from PyQt6.QtWidgets import (
    QApplication,
)
from PyQt6.QtCore import (
    QCommandLineParser,
    QCommandLineOption,
)
from PyQt6.QtWidgets import QStyleFactory
from sys import argv, exit
from shader_minifier.mainwindow import MainWindow
from shader_minifier.watcher import Watcher
from shader_minifier.version import Version
from shader_minifier.scheduler import Scheduler
from shader_minifier.entropy import Entropy
from shader_minifier.vcs import VCS
from typing import (
    List,
    Optional,
)
from pathlib import Path
from platform import system


if __name__ == '__main__':
    application: QApplication = QApplication(argv)

    application.setApplicationName('pyshader_minifier')
    application.setApplicationVersion(Version().describe())

    print(QStyleFactory.keys())
    if system() == 'Windows':
        application.setStyle('Fusion')

    parser: QCommandLineParser = QCommandLineParser()
    parser.setApplicationDescription("A CLI, GUI tool and library to interface the CTRL-ALT-TEST-minifier effectively.")
    parser.addHelpOption()
    parser.addVersionOption()
    parser.addOption(QCommandLineOption(["b", "build"], "Command line that builds your intro and has linker output with entropy in stdout.", "command"))
    parser.addOption(QCommandLineOption(["w", "working-directory"], "Working directory to run the build command in.", "command"))
    parser.addPositionalArgument("file", "Shader source to watch.", "[file]")
    parser.process(application)

    repository: Optional[VCS] = None
    repository = VCS()

    entropy: Entropy = Entropy(
        parser.value('build').split(' ') if parser.isSet('build') else None,
        Path(parser.value("working-directory")) if parser.isSet("working-directory") else None,
    )
    watcher: Watcher = Watcher()
    mainWindow: MainWindow = MainWindow()
    scheduler: Scheduler = Scheduler()

    # Start the threads.
    repository.start()
    watcher.start()
    entropy.start()
    scheduler.start()

    # Connect repository.
    repository.hasRepoChanged.connect(mainWindow.actionCommit.setEnabled)

    # Connect entropy.
    entropy.built.connect(mainWindow.updateModelsFromEntropy)

    # Connect watcher.
    watcher.fileLoaded.connect(mainWindow.fileChanged)
    watcher.historyExported.connect(mainWindow.historyExported)
    watcher.fileChanged.connect(mainWindow.updateModelsFromWatcher)
    watcher.fileChanged.connect(lambda _watcher: scheduler.minifyShader(_watcher.latestHash, _watcher._versions[_watcher.latestHash]))
    watcher.fileChanged.connect(lambda _watcher: entropy.determineEntropy(_watcher.latestHash))
    watcher.fileLoaded.connect(scheduler.reset)
    
    # Connect scheduler.
    scheduler.minifiersObtained.connect(watcher.updateFile)
    scheduler.versionsUpdated.connect(mainWindow.updateModelsFromScheduler)

    # Connect main window.
    def cleanup() -> None:
        scheduler.stop()
        entropy.stop()
        watcher.stop()
        repository.stop()

        scheduler._thread.join()
        entropy._thread.join()
        watcher._thread.join()
        repository._thread.join()

        QApplication.exit(0)

    def open(path: str) -> None:
        entropy.reset()
        scheduler.reset()

        if watcher.receivers(watcher.resetted) != 0:
            watcher.resetted.disconnect()
        watcher.resetted.connect(lambda path=path: watcher.watchFile(path))
        # watcher.resetted.connect(watcher.updateFile)
        watcher.reset()

        if repository.receivers(repository.resetted) != 0:
            repository.resetted.disconnect()
        repository.resetted.connect(lambda path=path: repository.changeShader(Path(path)))
        # repository.resetted.connect(watcher.updateFile)
        repository.reset()

    def changeMinifier(version: str) -> None:
        scheduler.selectMinifier(version)
        if watcher._path is not None:
            open(str(watcher._path))
        watcher.resetted.connect(watcher.updateFile)

    mainWindow.quitRequested.connect(cleanup)
    mainWindow.exportRequested.connect(watcher.saveHistory)
    mainWindow.commitRequested.connect(repository.createCommit)
    mainWindow.minifierVersionRequested.connect(changeMinifier)

    # Set up state from command line args.
    arguments: List[str] = parser.positionalArguments()
    if len(arguments) > 0:
        open(arguments[0])
        scheduler.minifiersObtained.connect(watcher.updateFile)
    
    if len(arguments) > 1:
        print("Warning: Ignoring additional positional CLI arguments: `{}`.".format(','.join(arguments[1:])))

    mainWindow.show()

    QApplication.exit(application.exec())
