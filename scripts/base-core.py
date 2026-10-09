#!/usr/bin/env python3
"""Expose nested Snap assets as normal files; keep each LFS source below 2 GiB."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import media

ROOT=Path(__file__).resolve().parents[1]


def run(*args): subprocess.run(args,check=True)


def build():
    if os.geteuid()!=0: raise ValueError('Run in a private user namespace')
    descriptor=ROOT/'base/system-layer.json'
    if descriptor.exists(): return
    original=ROOT/'base/media/casper/minimal.squashfs'
    core=ROOT/'base/media/casper/minimal.core.squashfs'
    work=ROOT/'build/base-core'
    if work.exists() or core.exists(): raise ValueError('Incomplete base-core build exists; preserve it before retry')
    work.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('rootfs_trim',ROOT/'scripts/rootfs-trim.py')
    trim=importlib.util.module_from_spec(spec);spec.loader.exec_module(trim)
    info=trim.metadata(original)
    snap_tree=work/'snap-tree'
    patterns=['var/lib/snapd/seed/snaps/*.snap','var/lib/snapd/snaps/*.snap']
    run('unsquashfs','-no-progress','-processors','2','-strict-errors','-d',str(snap_tree),str(original),*patterns)
    assets=ROOT/'base/snaps';assets.mkdir(exist_ok=True)
    entries=[]
    for path in sorted(snap_tree.rglob('*.snap')):
        if not path.is_file() or path.is_symlink(): raise ValueError('Unexpected snap asset')
        destination=assets/path.name
        checksum=media.digest(path)
        if destination.exists():
            if media.digest(destination)!=checksum: raise ValueError('Conflicting asset filenames')
        else: shutil.copy2(path,destination)
        if destination.stat().st_size>=2_147_483_648: raise ValueError('Natural asset exceeds 2 GiB')
        st=path.stat()
        entries.append(dict(file=destination.relative_to(ROOT).as_posix(),path=path.relative_to(snap_tree).as_posix(),
                            bytes=st.st_size,sha256=checksum,mode=st.st_mode&0o7777,uid=st.st_uid,gid=st.st_gid,mtime=int(st.st_mtime)))
    root=work/'rootfs'
    run('unsquashfs','-no-progress','-processors','4','-strict-errors','-xattrs-exclude','^trusted[.]overlay[.]',
        '-d',str(root),'-excludes',str(original),*patterns,*(d['path'] for d in info['devices']))
    trim.pseudo(work/'devices.pseudo',info,source=root)
    run('mksquashfs',str(root),str(core),'-noappend','-comp','zstd','-Xcompression-level','15',
        '-b','1048576','-processors','4','-no-progress','-pf',str(work/'devices.pseudo'))
    if core.stat().st_size>=2_147_483_648:
        raise ValueError('Core still exceeds 2 GiB; review compression before publishing')
    record=dict(original_layer_sha256=media.digest(original),core=core.relative_to(ROOT).as_posix(),
                core_sha256=media.digest(core),snaps=entries)
    descriptor.write_text(json.dumps(record,indent=2)+'\n')
    original.unlink()


if __name__=='__main__': build()
