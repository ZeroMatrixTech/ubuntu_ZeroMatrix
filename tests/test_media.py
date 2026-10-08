import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('media', Path(__file__).resolve().parents[1] / 'scripts/media.py')
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.original = media.ROOT
        media.ROOT = self.root
        (self.root / 'config').mkdir()
        (self.root / 'config/packages.txt').write_text('sample\n')
        self.source = self.root / 'input'
        self.source.mkdir()

    def tearDown(self):
        media.ROOT = self.original
        self.temp.cleanup()

    def deb(self, version='1.0', arch='amd64'):
        tree = self.root / f'package-{version}'
        (tree / 'DEBIAN').mkdir(parents=True)
        (tree / 'DEBIAN/control').write_text(
            f'Package: sample\nVersion: {version}\nArchitecture: {arch}\n'
            'Maintainer: Test <test@example.invalid>\nDescription: test fixture\n')
        output = self.source / f'sample_{version}_{arch}.deb'
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(tree), str(output)],
                       check=True, stdout=subprocess.DEVNULL)
        return output

    def test_bundle_records_exact_versions_and_refuses_overwrite(self):
        self.deb()
        media.bundle(self.source)
        repo = self.root / 'offline/repo'
        self.assertEqual(media.inventory(repo)[0]['version'], '1.0')
        self.assertIn('Package: sample', (repo / 'Packages').read_text())
        with self.assertRaises(ValueError):
            media.bundle(self.source)

    def test_wrong_architecture_rejected(self):
        self.deb(arch='arm64')
        with self.assertRaises(ValueError):
            media.inventory(self.source)

    def test_duplicate_version_rejected(self):
        self.deb()
        self.deb(version='2.0')
        with self.assertRaises(ValueError):
            media.inventory(self.source)

    def test_incomplete_requested_set_rejected(self):
        self.deb()
        (self.root / 'config/packages.txt').write_text('sample\nmissing\n')
        with self.assertRaises(ValueError):
            media.bundle(self.source)
        self.assertFalse((self.root / 'offline/repo').exists())


if __name__ == '__main__':
    unittest.main()
