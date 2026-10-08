#!/usr/bin/env python3
"""Import and validate pinned, platform-specific VS Code extension packages."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inspect(path):
    with zipfile.ZipFile(path) as z:
        info = json.loads(z.read('extension/package.json'))
        manifest = ET.fromstring(z.read('extension.vsixmanifest'))
        platforms = [node.attrib['Value'] for node in manifest.iter()
                     if node.attrib.get('Id') == 'Microsoft.VisualStudio.Code.TargetPlatform']
        platforms.extend(node.attrib['TargetPlatform'] for node in manifest.iter() if 'TargetPlatform' in node.attrib)
        if len(set(platforms)) > 1:
            raise ValueError('Conflicting VSIX platform metadata')
        platform = platforms[0] if platforms else 'universal'
        if platform not in ('universal', 'linux-x64'):
            raise ValueError(f'{path.name}: expected linux-x64 or universal, got {platform}')
        identifier = info['publisher'] + '.' + info['name']
        names = z.namelist()
        # Platform VSIX must already contain native backends; do not rely on first-start downloads.
        needed = {'ms-vscode.cpptools': ('cpptools', 'OpenDebugAD7'),
                  'rust-lang.rust-analyzer': ('rust-analyzer',),
                  'vadimcn.vscode-lldb': ('codelldb',)}
        for binary in needed.get(identifier, ()):
            if not any(Path(name).name == binary for name in names):
                raise ValueError(f'{identifier}: offline native backend {binary} is missing')
        if identifier in needed and platform != 'linux-x64':
            raise ValueError(f'{identifier}: use the linux-x64 platform VSIX')
    return dict(file=path.name, id=identifier, version=info['version'], platform=platform,
                engine=info.get('engines', {}).get('vscode'),
                dependencies=info.get('extensionDependencies', []), pack=info.get('extensionPack', []), sha256=sha(path))


def validate(directory):
    files = sorted(directory.glob('*.vsix'))
    if not files:
        raise ValueError('No offline VSIX packages found')
    if any(not all(c.isalnum() or c in '._-+' for c in p.name) for p in files):
        raise ValueError('VSIX filenames must use letters, digits, dots, underscores, plus or hyphens')
    records = [inspect(p) for p in files]
    ids = {r['id'] for r in records}
    if len(ids) != len(records):
        raise ValueError('Duplicate extension versions supplied')
    required = set(json.loads((ROOT / 'config/editor-extensions.json').read_text()))
    missing = required - ids
    for record in records:
        missing.update((set(record['dependencies']) | set(record['pack'])) - ids)
    if missing:
        raise ValueError('Missing required/dependency VSIX packages: ' + ', '.join(sorted(missing)))
    # Install dependencies first so VS Code does not resolve them from Marketplace.
    ordered = []
    while records:
        ready = [r for r in records if set(r['dependencies']) <= {x['id'] for x in ordered}]
        if not ready:
            raise ValueError('Cyclic extension dependencies')
        for record in ready:
            ordered.append(record)
            records.remove(record)
    return ordered


def locked(directory):
    records = validate(directory)
    if records != json.loads((directory / 'manifest.json').read_text()):
        raise ValueError('VSIX files differ from the locked extension manifest')
    return records


def bundle(source):
    destination = ROOT / 'offline/editor'
    if destination.exists():
        raise ValueError('offline/editor exists; prepare a new checkout for an updated bundle')
    records = validate(source)
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as t:
        staged = Path(t) / 'editor'
        staged.mkdir()
        for record in records:
            shutil.copy2(source / record['file'], staged / record['file'])
        if (source / 'acquisition.json').is_file():
            shutil.copy2(source / 'acquisition.json', staged / 'acquisition.json')
        (staged / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
        staged.rename(destination)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    args = p.parse_args()
    bundle(args.source.resolve(strict=True))
