from typing import (
    Self,
    Dict,
    List,
    Optional,
)
from enum import (
    IntEnum,
    StrEnum,
    auto,
)
from subprocess import (
    run,
    CompletedProcess,
)
from pathlib import Path
from cached_path import cached_path
from parse import parse
from hashlib import sha256
from tempfile import TemporaryDirectory
from platform import system
from stat import S_IEXEC


class ShaderMinifierError(Exception):
    pass


class ValidationError(Exception):
    pass


class ObtainmentStrategy(IntEnum):
    EnvironmentVariables = auto()
    Download = auto()


class MinifierVersion(IntEnum):
    unavailable = auto()
    v1_4_0 = auto()
    v1_3_6 = auto()
    v1_3_5 = auto()
    v1_3_4 = auto()
    v1_3_3 = auto()
    v1_3_2 = auto()
    v1_3_1 = auto()
    v1_3 = auto()
    v1_2 = auto()
    v1_1_6 = auto()


class MinifierOutputFormat(StrEnum):
    Text = 'text'
    Indented = 'indented'
    CVariables = 'c-variables'
    JavaScript = 'js'
    Nasm = 'nasm'
    Rust = 'rust'


class MinifierSwizzleType(StrEnum):
    RGBA = 'rgba'
    XYZW = 'xyzw'
    STPQ = 'stpq'


class shader_minifier:
    if system() == 'Windows':
        validatorUrl: str = 'https://github.com/KhronosGroup/glslang/releases/download/master-tot/glslang-master-windows-x64-Release.zip!bin/glslangValidator.exe'
        Locator: str = 'where'
        CRLF: str = '\r\n'
    else:
        validatorUrl: str = 'https://github.com/KhronosGroup/glslang/releases/download/main-tot/glslang-main-linux-Release.zip!bin/glslangValidator'
        Locator: str = 'which'
        CRLF: str = '\n'

    hashes: Dict[MinifierVersion, str] = {
        MinifierVersion.v1_1_6: '6ce3e12ab598c35a8eb9edf108928c6d43d828b475124eddeed299546318c9a1',
        MinifierVersion.v1_2: 'c91a6109bce3f0bf40573893628dd29c61b4ec498a5f08a8b32d553ae7b57a5a',
        MinifierVersion.v1_3: 'b4f3790d6f6d7ba090cc5ce412aa175362105a156fa0b68fc0be9a4fa4158af7',
        MinifierVersion.v1_3_1: '200020d7c1ffc481625d56ec0294e2d3321a92daf52fb27f80fb5c95a0617939',
        MinifierVersion.v1_3_2: 'a0b25ca99e40d35ca1b8f88e5a3ef512205b82188ec8077d74734005b117abe6',
        MinifierVersion.v1_3_3: '3c12749684c394dcf3a19a274eb9ae28b0fb3d77e859ef2c3f63ed33def49fb9',
        MinifierVersion.v1_3_4: '5c7da81cb612e9367596197c6f6d3d798686542d3c312d3c12bf211a23e79bdc',
        MinifierVersion.v1_3_5: '6fe8dce492bb3b25c1f13e910d72a26ed22bce5765b0eed9922d2f1ed58a6681',
        MinifierVersion.v1_3_6: 'c71e0ac9c2e73083e4d5faa232382dee1c1665b5f494fc2abebb89fa90c5aa1f',
        MinifierVersion.v1_4_0: '7a4bd1605a0e3d3cc501265a439be2888c4865c3694518f7ba41200f5808d610',
    }
    validatorHash: str = '64df5da3b9b496b764fe7884fb730814639bf4b200da6fc4ed5fb1d6fc506302'

    @staticmethod
    def versionString(version: MinifierVersion) -> str:
        return version.name[1:].replace('_', '.')
    
    @staticmethod
    def versionFromString(versionString: str) -> MinifierVersion:
        return MinifierVersion['v{}'.format(versionString.replace('.', '_'))]

    urls: Dict[MinifierVersion, str] = {}
    for version in MinifierVersion:
        urls[version] = 'https://github.com/laurentlb/Shader_Minifier/releases/download/{}/shader_minifier.exe'.format(versionString(version))

    @staticmethod
    def determineVersion(path: Path) -> MinifierVersion:
        if path.is_dir():
            return MinifierVersion.unavailable

        try:
            result: Optional[CompletedProcess] = run(
                [
                    path, '--help',
                ],
                capture_output=True,
            )
            
            lines: List[str] = result.stdout.decode('utf-8').split(shader_minifier.CRLF)
            if len(lines) < 1:
                return MinifierVersion.unavailable
            
            versionString = parse('Shader Minifier {} - https://github.com/laurentlb/Shader_Minifier', lines[0])[0]
            return shader_minifier.versionFromString(versionString)

        except FileNotFoundError:
            return MinifierVersion.unavailable

    def __init__(
        self: Self,
        version: MinifierVersion=MinifierVersion.v1_3_6,
        obtain: ObtainmentStrategy=ObtainmentStrategy.EnvironmentVariables,
    ) -> None:
        # Find or get shader_minifier
        path: Optional[Path] = None
        if obtain == ObtainmentStrategy.EnvironmentVariables:
            result: Optional[CompletedProcess] = run(
                [
                    shader_minifier.Locator, 'shader_minifier',
                ],
                capture_output=True,
            )
            if result.returncode == 0:
                paths: List[Path] = list(filter(
                    lambda pathOption: shader_minifier.determineVersion(pathOption) == version,
                    map(
                        lambda pathString: Path(pathString.rstrip()),
                        result.stdout.decode('utf-8').split(shader_minifier.CRLF),
                    ),
                ))

                if len(paths) == 0:
                    # All shader_minifier executables in PATH have the wrong version. Download it.
                    obtain = ObtainmentStrategy.Download
                else:
                    path = paths[0]
            
            else:
                # No shader_minifier executable found in PATH. Download it.
                obtain = ObtainmentStrategy.Download

        if obtain == ObtainmentStrategy.Download:
            path = cached_path(shader_minifier.urls[version], quiet=True)
            path.chmod(path.stat().st_mode | S_IEXEC)
            assert sha256(path.read_bytes()).digest() == bytes.fromhex(shader_minifier.hashes[version])

        # Find or get glslangValidator
        validator: Optional[Path] = None
        downloadValidator: bool = False
        result: Optional[CompletedProcess] = run(
            [
                shader_minifier.Locator, 'glslangValidator',
            ],
            capture_output=True,
        )
        if result.returncode == 0:
            paths: List[Path] = list(map(
                lambda pathString: Path(pathString.rstrip()),
                result.stdout.decode('utf-8').split(shader_minifier.CRLF),
            ))

            if len(paths) == 0:
                downloadValidator = True
            else:
                validator = paths[0]
        else:
            downloadValidator = True

        if downloadValidator:
            validator = cached_path(shader_minifier.validatorUrl, extract_archive=True)
            validator.chmod(validator.stat().st_mode | S_IEXEC)
            assert sha256(validator.read_bytes()).digest() == bytes.fromhex(shader_minifier.validatorHash)

        self._path: Path = path
        self._version: MinifierVersion = version
        self._obtain: ObtainmentStrategy = obtain
        self._validator: Path = validator

    @property
    def version(self: Self) -> MinifierVersion:
        return self._version

    @property
    def path(self: Self) -> Path:
        return self._path
    
    def validate(self: Self, source: str) -> bool:
        with TemporaryDirectory() as tempDir:
            (Path(tempDir) / 'shader.frag').write_text(source)

            result: CompletedProcess = run(
                [
                    self._validator,
                    Path(tempDir) / 'shader.frag',
                ],
                capture_output=True,
            )

            if result.returncode != 0:
                raise ValidationError(result.stdout.decode('utf-8'))

    def minify(
        self: Self,
        source: str,
        verbose: bool = False,
        hlsl: bool = False,
        format: MinifierOutputFormat = MinifierOutputFormat.Indented,
        field_names: MinifierSwizzleType = MinifierSwizzleType.RGBA,
        preserve_externals: bool = False,
        preserve_globals: bool = False,
        no_inlining: bool = False,
        aggressive_inlining: bool = False,
        no_renaming: bool = False,
        no_renaming_list: Optional[List[str]] = None,
        no_sequence: bool = None,
        smoothstep: bool = False,
        no_remove_unused: bool = False,
        move_declarations: bool = False,
        preprocess: bool = False,
    ) -> Optional[str]:
        with TemporaryDirectory() as tempDir:
            (Path(tempDir) / 'unminified.frag').write_text(source)

            # Validate unminified shader
            result: CompletedProcess = run(
                [
                    self._validator,
                    Path(tempDir) / 'unminified.frag',
                ],
                capture_output=True,
            )

            if result.returncode != 0:
                raise ValidationError(result.stdout.decode('utf-8'))

            # Minify shader
            result: CompletedProcess = run(
                ' '.join([
                    '\"{}\"'.format(self._path),
                    '-o', '\"{}\"'.format(Path(tempDir) / 'minified.frag'),
                    '-v' if verbose else '',
                    '--hlsl' if hlsl else '',
                    '--format', format.value,
                    '--field-names', field_names.value,
                    '--preserve-externals' if preserve_externals else '',
                    '--preserve-all-globals' if preserve_globals else '',
                    '--no-inlining' if no_inlining else '',
                    '--aggressive-inlining' if aggressive_inlining else '',
                    '--no-renaming' if no_renaming else '',
                    '--no-renaming-list' if no_renaming_list is not None else '', ','.join(no_renaming_list) if no_renaming_list is not None else ''
                    '--no-sequence' if no_sequence else '',
                    '--smoothstep' if smoothstep else '',
                    '--no-remove-unused' if no_remove_unused else '',
                    '--move-declarations' if move_declarations else '',
                    '--preprocess' if preprocess else '',
                    '\"{}\"'.format(Path(tempDir) / 'unminified.frag'),
                ]),
                capture_output=True,
                shell=True,
            )

            if result.returncode != 0:
                raise ShaderMinifierError(result.stdout.decode('utf-8'))

            # Validate minified shader
            result: CompletedProcess = run(
                [
                    self._validator,
                    Path(tempDir) / 'minified.frag',
                ],
                capture_output=True,
            )

            if result.returncode != 0:
                raise ValidationError('Invalid minified shader - \n{}\n >>> THIS IS A SHADER_MINIFIER_BUG. REPORT IT TO https://github.com/laurentlb/Shader_Minifier/issues !!\n'.format(result.stdout))

            # Return minified result
            return (Path(tempDir) / 'minified.frag').read_text()
