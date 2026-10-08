#!/usr/bin/env python3
"""Locate, inspect and lock the locally supplied VS Code Debian package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def locate():
    explicit = os.environ.get('CODE_DEB', '').strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else ROOT / path
    lock = ROOT / 'config/code-package.json'
    if lock.exists():
        filename = json.loads(lock.read_text())['file']
        if Path(filename).name != filename:
            raise ValueError('The locked package filename must be relative to the repository root')
        return ROOT / filename
    candidates = sorted(ROOT.glob('code_*_amd64.deb'))
    if len(candidates) != 1:
        raise ValueError('Supply exactly one code_*_amd64.deb in the repository, or set CODE_DEB')
    return candidates[0]


def inspect(path):
    path = path.resolve(strict=True)
    fields = {}
    for field in ('Package', 'Version', 'Architecture'):
        fields[field.lower()] = subprocess.check_output(['dpkg-deb', '-f', str(path), field], text=True).strip()
    if fields['package'] != 'code' or fields['architecture'] != 'amd64':
        raise ValueError('Expected a VS Code (code) amd64 Debian package')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return dict(file=path.name, **fields, bytes=path.stat().st_size, sha256=h.hexdigest())


def validate(path):
    record = inspect(path)
    lock = ROOT / 'config/code-package.json'
    if not lock.is_file():
        raise ValueError('Run make code-lock to record the imported VS Code package first')
    expected = json.loads(lock.read_text())
    if any(record[key] != expected[key] for key in ('package', 'version', 'architecture', 'bytes', 'sha256')):
        raise ValueError('VS Code package differs from config/code-package.json; review it and run make code-lock for an intentional update')
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('info', 'lock', 'path'))
    args = p.parse_args()
    try:
        path = locate()
        if args.command == 'lock':
            record = inspect(path)
            destination = ROOT / 'config/code-package.json'
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(json.dumps(record, indent=2) + '\n')
        else:
            record = validate(path)
        if args.command == 'path':
            print(path.resolve())
        else:
            print(json.dumps(record, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'VS Code input error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
