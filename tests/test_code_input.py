import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('code_input', Path(__file__).resolve().parents[1] / 'scripts/code-input.py')
code = importlib.util.module_from_spec(spec)
spec.loader.exec_module(code)


class CodeInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(code, 'ROOT', self.root)
        self.root_patch.start()
        self.env_patch = patch.dict(os.environ, {'CODE_DEB': ''})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def package(self, arch='amd64'):
        tree = self.root / 'package'
        (tree / 'DEBIAN').mkdir(parents=True)
        (tree / 'DEBIAN/control').write_text(
            f'Package: code\nVersion: 1.0\nArchitecture: {arch}\n'
            'Maintainer: Fixture <fixture@example.invalid>\nDescription: test\n')
        target = self.root / f'code_1.0_{arch}.deb'
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(tree), str(target)],
                       check=True, stdout=subprocess.DEVNULL)
        return target

    def test_autodetect_and_reject_modified_input(self):
        package = self.package()
        self.assertEqual(code.locate(), package)
        record = code.inspect(package)
        (self.root / 'config').mkdir()
        (self.root / 'config/code-package.json').write_text(json.dumps(record))
        self.assertEqual(code.validate(package), record)
        record['sha256'] = '0' * 64
        (self.root / 'config/code-package.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'differs'):
            code.validate(package)

    def test_wrong_architecture_rejected(self):
        with self.assertRaisesRegex(ValueError, 'amd64'):
            code.inspect(self.package('arm64'))

    def test_multiple_packages_require_explicit_selection(self):
        (self.root / 'code_1_amd64.deb').touch()
        (self.root / 'code_2_amd64.deb').touch()
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            code.locate()
        with patch.dict(os.environ, {'CODE_DEB': 'code_2_amd64.deb'}):
            self.assertEqual(code.locate(), self.root / 'code_2_amd64.deb')


if __name__ == '__main__':
    unittest.main()
