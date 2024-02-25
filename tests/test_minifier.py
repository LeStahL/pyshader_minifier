from unittest import (
    TestCase,
    main,
)
from typing import (
    Self,
)
from shader_minifier import (
    shader_minifier,
    MinifierVersion,
    ObtainmentStrategy,
    ValidationError,
    ShaderMinifierError,
)
from importlib.resources import files
import tests


class TestMinifier(TestCase):
    SimpleShaderSource: str = (files(tests) / 'simple_shader.frag').read_text()
    SimpleErrorShaderSource: str = (files(tests) / 'simple_error_shader.frag').read_text()

    def testPath(self: Self) -> None:
        minifier: shader_minifier = shader_minifier()
        self.assertEqual(minifier.version, MinifierVersion.v1_3_6)

    def testDownload(self: Self) -> None:
        minifier: shader_minifier = shader_minifier(
            version=MinifierVersion.v1_3_3,
            obtain=ObtainmentStrategy.Download,
        )
        self.assertEqual(shader_minifier.determineVersion(minifier.path), MinifierVersion.v1_3_3)

    def testMinify(self: Self) -> None:
        result: str = shader_minifier().minify(TestMinifier.SimpleShaderSource)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, '')

    def testMinifyError(self: Self) -> None:
        with self.assertRaises(ValidationError) as error:
            shader_minifier().minify(TestMinifier.SimpleErrorShaderSource)


if __name__ == '__main__':
    main()
