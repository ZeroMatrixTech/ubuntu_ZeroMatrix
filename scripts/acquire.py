#!/usr/bin/env python3
"""Download the reviewed, checksum-locked input set without installing host software."""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_filename(value):
    if not re.fullmatch(r'[A-Za-z0-9_.+:%~-]+', value) or value in ('.', '..'):
        raise ValueError('Invalid input filename')
    return value


def fetch(url, destination, checksum=None):
    host = urlparse(url).hostname or ''
    if urlparse(url).scheme != 'https' or not (
        host in ('releases.ubuntu.com', 'archive.ubuntu.com', 'security.ubuntu.com', 'github.com')
        or host.endswith('.gallerycdn.vsassets.io')
    ):
        raise ValueError('Unexpected input source: ' + host)
    media = load('input_hash', 'media.py')
    if checksum and destination.is_file() and media.digest(destination) == checksum:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + '.part')
    subprocess.run(['curl', '-fL', '--silent', '--show-error', '--retry', '2',
                    '--connect-timeout', '20', '--max-time', '300', url, '-o', str(partial)], check=True)
    if checksum and media.digest(partial) != checksum:
        raise ValueError('Downloaded input checksum mismatch: ' + destination.name)
    partial.replace(destination)


def acquire():
    for tool in ('curl', 'gpgv', 'dpkg-deb', 'dpkg-scanpackages'):
        if shutil.which(tool) is None:
            raise ValueError('Missing acquisition tool: ' + tool)
    work = Path(os.environ.get('ACQUIRE_DIR') or ROOT / 'build/acquire').expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)
    media = load('input_media', 'media.py')
    code_input = load('input_code', 'code-input.py')
    code_file = code_input.locate()
    code = code_input.validate(code_file)
    base = json.loads((ROOT / 'config/base-iso.json').read_text())
    iso = Path(os.environ.get('BASE_ISO') or base['file']).expanduser()
    if not iso.is_absolute():
        iso = ROOT / iso
    trust = work / 'trust'
    trust.mkdir(exist_ok=True)
    fetch(base['checksums_url'], trust / 'SHA256SUMS')
    fetch(base['signature_url'], trust / 'SHA256SUMS.gpg')
    signature = subprocess.run(['gpgv', '--keyring', '/usr/share/keyrings/ubuntu-archive-keyring.gpg',
                               str(trust / 'SHA256SUMS.gpg'), str(trust / 'SHA256SUMS')],
                              check=True, capture_output=True, text=True)
    (trust / 'signature-verification.txt').write_text(signature.stderr)
    listed = {}
    for line in (trust / 'SHA256SUMS').read_text().splitlines():
        checksum, name = line.split(maxsplit=1)
        listed[name.lstrip('*')] = checksum
    if listed.get(base['file']) != base['sha256'] or media.digest(iso) != base['sha256']:
        raise ValueError('Base ISO does not match the signed official checksum and reviewed lock')
    packages = json.loads((ROOT / 'config/packages-acquisition.json').read_text())
    extensions = json.loads((ROOT / 'config/editor-acquisition.json').read_text())
    jobs = []
    debs, vsix = work / 'inputs/debs', work / 'inputs/vsix'
    debs.mkdir(parents=True, exist_ok=True)
    vsix.mkdir(parents=True, exist_ok=True)
    for record in packages:
        destination = debs / safe_filename(record['file'])
        if record.get('local'):
            if record['package'] != 'code' or record['sha256'] != code['sha256']:
                raise ValueError('Local code input differs from package acquisition lock')
            if not destination.exists() or media.digest(destination) != code['sha256']:
                shutil.copy2(code_file, destination)
        else:
            jobs.append((record['url'], destination, record['sha256']))
    for record in extensions:
        jobs.append((record['url'], vsix / safe_filename(record['file']), record['sha256']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch, *job) for job in jobs]
        for future in futures:
            future.result()
    (debs / 'acquisition.json').write_text(json.dumps(packages, indent=2) + '\n')
    (vsix / 'acquisition.json').write_text(json.dumps(extensions, indent=2) + '\n')
    if not (ROOT / 'offline/repo').exists():
        media.bundle(debs)
    actual = media.inventory(ROOT / 'offline/repo')
    expected = [{k: p[k] for k in ('file', 'package', 'version', 'architecture', 'bytes', 'sha256')}
                for p in packages]
    if actual != expected:
        raise ValueError('Existing package bundle differs from the acquisition lock; use a new build checkout')
    editor = load('input_editor', 'editor.py')
    if not (ROOT / 'offline/editor').exists():
        editor.bundle(vsix)
    actual_extensions = editor.locked(ROOT / 'offline/editor')
    expected_extensions = {p['id']: (p['version'], p['sha256']) for p in extensions}
    if {p['id']: (p['version'], p['sha256']) for p in actual_extensions} != expected_extensions:
        raise ValueError('Existing editor bundle differs from the reviewed acquisition lock')
    (ROOT / 'offline/trust').mkdir(parents=True, exist_ok=True)
    for path in trust.iterdir():
        if path.is_file():
            shutil.copy2(path, ROOT / 'offline/trust' / path.name)
    (ROOT / 'config/base-iso.sha256').write_text(base['sha256'] + '\n')
    print(f'Acquired and verified {len(packages)} Debian packages and {len(extensions)} VSIX files.')
    print('Run make iso. ACLt seed is prepared separately with make workspace if not already present.')


if __name__ == '__main__':
    try:
        acquire()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('Acquisition stopped:', error, file=sys.stderr)
        sys.exit(1)
