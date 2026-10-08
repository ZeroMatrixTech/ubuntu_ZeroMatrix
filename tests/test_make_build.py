import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('make_build', Path(__file__).resolve().parents[1] / 'scripts/make-build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class MakeBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='make build ')
        self.root = Path(self.temp.name)
        (self.root / 'VERSION').write_text('0.1.0-rc1\n')
        self.root_patch = patch.object(build, 'ROOT', self.root)
        self.root_patch.start()
        self.env_patch = patch.dict(os.environ, {'VERSION': '', 'BASE_ISO': '', 'BASE_SHA256': ''})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def test_current_version_and_persisted_checksum(self):
        (self.root / 'config').mkdir()
        (self.root / 'config/base-iso.sha256').write_text('a' * 64 + '\n')
        version, base, checksum = build.settings()
        self.assertEqual(version, '0.1.0-rc1')
        self.assertEqual(base, self.root / 'ubuntu-26.04.1-desktop-amd64.iso')
        self.assertEqual(checksum, 'a' * 64)

    def test_missing_verified_checksum_stops_build(self):
        with self.assertRaisesRegex(ValueError, 'officially verified'):
            build.settings()

    def test_explicit_values_support_paths_with_spaces(self):
        with patch.dict(os.environ, {'VERSION': '0.2.0', 'BASE_SHA256': 'B' * 64,
                                     'BASE_ISO': 'media images/base.iso'}):
            version, base, checksum = build.settings()
        self.assertEqual(version, '0.2.0')
        self.assertEqual(base, self.root / 'media images/base.iso')
        self.assertEqual(checksum, 'b' * 64)

    def test_version_cannot_escape_output_directory(self):
        with patch.dict(os.environ, {'VERSION': '../../elsewhere'}):
            with self.assertRaisesRegex(ValueError, 'filename-safe'):
                build.settings()


if __name__ == '__main__':
    unittest.main()
