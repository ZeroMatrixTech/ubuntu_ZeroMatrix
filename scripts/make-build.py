#!/usr/bin/env python3
"""Make entry point; variables are read as data, never interpolated into a shell."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def path_from_root(value):
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def settings():
    version = os.environ.get('VERSION', '').strip() or (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.+-]*', version):
        raise ValueError('VERSION must be a nonempty filename-safe release version')
    base = path_from_root(os.environ.get('BASE_ISO') or 'ubuntu-26.04.1-desktop-amd64.iso')
    checksum = os.environ.get('BASE_SHA256', '').strip()
    checksum_file = ROOT / 'config/base-iso.sha256'
    if not checksum and checksum_file.is_file():
        checksum = checksum_file.read_text().strip()
    if not re.fullmatch(r'[a-fA-F0-9]{64}', checksum):
        raise ValueError('Set BASE_SHA256 to the officially verified 64-character SHA256, '
                         'or store that hash alone in config/base-iso.sha256')
    return version, base, checksum.lower()


def load_media():
    spec = importlib.util.spec_from_file_location('zeromatrix_media', ROOT / 'scripts/media.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check():
    missing = [tool for tool in ('bash', 'git', 'dpkg-deb', 'dpkg-scanpackages', 'xorriso')
               if shutil.which(tool) is None]
    if missing:
        raise ValueError('Missing build tools: ' + ', '.join(missing))
    version, base, checksum = settings()
    if not base.is_file():
        raise ValueError(f'Base ISO missing: {base}')
    repo = ROOT / 'offline/repo'
    if not (repo / 'manifest.json').is_file():
        raise ValueError('Offline bundle is not prepared. In a matching acquisition VM, download '
                         'the packages; then run make bundle DEBS_DIR=/path/to/debs')
    media = load_media()
    records = media.inventory(repo)
    if records != json.loads((repo / 'manifest.json').read_text()):
        raise ValueError('Offline packages differ from their locked manifest')
    required = {line.strip() for line in (ROOT / 'config/packages.txt').read_text().splitlines()
                if line.strip() and not line.lstrip().startswith('#')}
    absent = required - {p['package'] for p in records}
    if absent:
        raise ValueError('Offline bundle is missing requested packages: ' + ', '.join(sorted(absent)))
    code_lock = ROOT / 'config/code-package.json'
    if not code_lock.is_file():
        raise ValueError('Run make code-lock to record the VS Code package')
    expected_code = json.loads(code_lock.read_text())
    actual_code = next((p for p in records if p['package'] == 'code'), None)
    if actual_code is None or any(actual_code[k] != expected_code[k] for k in ('version', 'architecture', 'bytes', 'sha256')):
        raise ValueError('Offline code package differs from the selected VS Code input; rebuild the package bundle')
    media.workflow_inputs()
    output = ROOT / 'dist' / f'zeromatrix-{version}-amd64.iso'
    if output.with_suffix(output.suffix + '.partial').exists():
        raise ValueError('Previous partial ISO exists; preserve its evidence and use a new VERSION')
    if output.exists():
        raise ValueError(f'Output already exists: {output}. Use a new VERSION; no automatic overwrite.')
    print(f'Ready: {version}; {len(records)} packages; base={base}', flush=True)
    print('Base ISO SHA256 will be fully checked during the build.', flush=True)
    return version, base, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('check', 'iso', 'bundle', 'editor', 'workspace'))
    args = parser.parse_args()
    try:
        if args.command == 'check':
            check()
        elif args.command == 'iso':
            version, base, checksum = check()
            subprocess.run([sys.executable, str(ROOT / 'scripts/media.py'), 'build',
                            '--base', str(base), '--sha256', checksum, '--version', version],
                           cwd=ROOT, check=True)
        elif args.command in ('editor', 'workspace'):
            variable = 'VSIX_DIR' if args.command == 'editor' else 'ACLT_DIR'
            source = os.environ.get(variable, '').strip()
            if not source:
                raise ValueError(f'Set {variable} to the input directory')
            script = 'editor.py' if args.command == 'editor' else 'workspace.py'
            subprocess.run([sys.executable, str(ROOT / 'scripts' / script), str(path_from_root(source))],
                           cwd=ROOT, check=True)
        else:
            source = os.environ.get('DEBS_DIR', '').strip()
            if not source:
                raise ValueError('Usage: make bundle DEBS_DIR=/absolute/path/to/debs')
            subprocess.run([sys.executable, str(ROOT / 'scripts/media.py'), 'bundle',
                            str(path_from_root(source))], cwd=ROOT, check=True)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'Build stopped: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
