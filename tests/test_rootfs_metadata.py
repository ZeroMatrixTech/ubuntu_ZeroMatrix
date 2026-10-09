import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('trim_metadata',ROOT/'scripts/rootfs-trim.py')
trim=importlib.util.module_from_spec(spec);spec.loader.exec_module(trim)

@unittest.skipUnless(shutil.which('mksquashfs'),'squashfs-tools required')
class MetadataTests(unittest.TestCase):
    def test_real_whiteout_and_opaque_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';(source/'usr').mkdir(parents=True)
            (source/'usr'/"user's note").write_text('file names need no shell quoting')
            image=root/'image.squashfs'
            subprocess.run(['mksquashfs',str(source),str(image),'-noappend','-processors','1','-no-progress',
                            '-p','usr/deleted c 0000 0 0 0 0','-p','usr x trusted.overlay.opaque=y'],
                            check=True,stdout=subprocess.DEVNULL)
            info=trim.metadata(image)
            self.assertEqual(info['opaque'],['usr'])
            device=next(d for d in info['devices'] if d['path']=='usr/deleted')
            self.assertEqual((device['major'],device['minor']),('0','0'))
