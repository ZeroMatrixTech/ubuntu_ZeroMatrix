#!/usr/bin/env python3
"""Pass build paths as data, not interpolated shell commands."""
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
version=os.environ.get('VERSION','').strip() or (ROOT/'VERSION').read_text().strip()
work=os.environ.get('ROOTFS_BUILD') or f'build/rootfs-{version}'
subprocess.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork',
                'python3',str(ROOT/'scripts/rootfs-trim.py'),work],cwd=ROOT,check=True)
