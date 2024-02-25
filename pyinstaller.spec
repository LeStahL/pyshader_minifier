# -*- mode: python ; coding: utf-8 -*-
from os.path import abspath, join
from zipfile import ZipFile
from shader_minifier.version import Version
from platform import system
from pathlib import Path


moduleName = 'shader_minifier'
rootPath = Path(".")
buildPath = rootPath / 'build'
distPath = rootPath / 'dist'
sourcePath = rootPath / moduleName

version = Version()
version.generateVersionModule(buildPath)

block_cipher = None

a = Analysis(
    [
        sourcePath / '__main__.py',
    ],
    pathex=[],
    binaries=[],
    datas=[
        (buildPath / '{}.py'.format(Version.VersionModuleName), moduleName),
        (sourcePath / 'team210.ico', moduleName),
        (sourcePath / 'mainwindow.ui', moduleName),
    ],
    hiddenimports=[
        '_cffi_backend',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{}-{}'.format(moduleName, version.describe()),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=sourcePath / 'team210.ico'
)

exeFileName = '{}-{}{}'.format(moduleName, version.describe(), '.exe' if system() == 'Windows' else '')
zipFileName = '{}-{}-{}.zip'.format(moduleName, version.describe(), 'windows' if system() == 'Windows' else 'linux')

zipfile = ZipFile(distPath / zipFileName, mode='w')
zipfile.write(distPath / exeFileName, arcname=exeFileName)
zipfile.write(rootPath / 'README.md', arcname='README.md')
zipfile.write(rootPath / 'LICENSE', arcname='LICENSE')
zipfile.write(rootPath / 'screenshot.png', arcname='screenshot.png')
zipfile.close()
