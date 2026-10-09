#!/usr/bin/env python3
"""Import/verify a browsable ISO file tree, including its hidden boot images."""
import json
from pathlib import Path
import subprocess
import sys
import media

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'base'


def inventory():
    records={}
    for folder in ('media','boot','snaps'):
        for path in sorted((BASE/folder).rglob('*')):
            name=path.relative_to(BASE).as_posix()
            if path.is_symlink():
                records[name]={'symlink':str(path.readlink())}
            elif path.is_file():
                records[name]={'bytes':path.stat().st_size,'sha256':media.digest(path)}
    descriptor=BASE/'system-layer.json'
    if descriptor.exists(): records['system-layer.json']={'bytes':descriptor.stat().st_size,'sha256':media.digest(descriptor)}
    return records


def seal():
    lock=json.loads((ROOT/'config/base-iso.json').read_text())
    record=dict(original_iso=lock,files=inventory())
    if not record['files']: raise ValueError('No media tree to seal')
    (BASE/'tree-manifest.json').write_text(json.dumps(record,indent=2)+'\n')


def verify():
    record=json.loads((BASE/'tree-manifest.json').read_text())
    actual=inventory()
    if actual!=record['files']: raise ValueError('Base media tree changed or LFS files missing; import/review a new base')
    print(f'Base tree verified: {len(actual)} entries',flush=True)
    return record


def main(command):
    if command=='import':
        lock=json.loads((ROOT/'config/base-iso.json').read_text())
        original=ROOT/lock['file']
        if media.digest(original)!=lock['sha256']: raise ValueError('Original ISO SHA256 mismatch')
        if (BASE/'media').exists(): raise ValueError('Media tree exists; refusing overwrite')
        BASE.mkdir(exist_ok=True)
        subprocess.run(['xorriso','-osirrox','on','-indev',str(original),'-extract','/',str(BASE/'media'),'-extract_boot_images',str(BASE/'boot')],check=True)
        subprocess.run(['unshare','--user','--map-auto','--map-root-user','--mount','--pid','--fork',sys.executable,str(ROOT/'scripts/base-core.py')],check=True)
        seal()
    elif command=='seal': seal()
    elif command=='verify': verify()
    else: raise ValueError('Use import, seal or verify')


if __name__=='__main__': main(sys.argv[1])
