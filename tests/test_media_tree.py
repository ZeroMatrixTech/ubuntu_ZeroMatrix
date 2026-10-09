import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

tree=module('media_tree','media-tree.py')
trim=module('rootfs_trim','rootfs-trim.py')

class TreeTests(unittest.TestCase):
    def test_tampering_and_symlink_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/'base'
            (root/'config').mkdir();(root/'config/base-iso.json').write_text('{"sha256":"test"}')
            (base/'media').mkdir(parents=True);(base/'boot').mkdir();(base/'snaps').mkdir()
            source=base/'media/config.txt';source.write_text('original')
            (base/'media/ubuntu').symlink_to('.')
            with patch.object(tree,'ROOT',root),patch.object(tree,'BASE',base):
                tree.seal();tree.verify()
                self.assertEqual(tree.inventory()['media/ubuntu'],{'symlink':'.'})
                source.write_text('changed')
                with self.assertRaises(ValueError): tree.verify()

    def test_snap_restore_preserves_content_and_hardlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'base/snaps').mkdir(parents=True)
            source=root/'base/snaps/browser.snap';source.write_bytes(b'locked snap asset')
            record=dict(file='base/snaps/browser.snap',bytes=source.stat().st_size,
                        sha256=trim.media.digest(source),uid=os.getuid(),gid=os.getgid(),mode=0o644,mtime=100)
            records=[dict(record,path='var/lib/snapd/seed/snaps/browser.snap'),dict(record,path='var/lib/snapd/snaps/browser.snap')]
            descriptor=root/'base/system-layer.json';descriptor.write_text(json.dumps(dict(snaps=records)))
            output=root/'output';output.mkdir()
            with patch.object(trim,'ROOT',root):
                trim.restore_snap_assets(output)
            a=output/records[0]['path'];b=output/records[1]['path']
            self.assertEqual(a.read_bytes(),source.read_bytes())
            self.assertEqual(a.stat().st_ino,b.stat().st_ino)
            self.assertEqual(a.stat().st_mtime,100)

    def test_snap_restore_rejects_unsafe_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'base').mkdir()
            (root/'base/system-layer.json').write_text('{"snaps":[{"path":"../escape"}]}')
            with patch.object(trim,'ROOT',root),self.assertRaises(ValueError): trim.restore_snap_assets(root/'out')
