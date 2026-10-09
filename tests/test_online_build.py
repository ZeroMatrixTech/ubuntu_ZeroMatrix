import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('online',ROOT/'scripts/build-online.py')
online=importlib.util.module_from_spec(spec)
spec.loader.exec_module(online)

class OnlineBuildTests(unittest.TestCase):
    def test_vm_safe_default_and_physical_normal_default(self):
        original='linux /casper/vmlinuz\ninitrd /casper/initrd\n'
        vm=online.boot(original,'vm')
        physical=online.boot(original,'physical')
        self.assertIn('nomodeset',vm.split('menuentry')[1])
        self.assertNotIn('nomodeset',physical.split('menuentry')[1])
        self.assertTrue(vm.endswith(original))

    def test_reject_unexpected_base(self):
        with self.assertRaises(ValueError): online.boot('unknown','vm')
