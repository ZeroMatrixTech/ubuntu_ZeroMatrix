#!/usr/bin/env python3
"""Build checksum-locked offline payloads and boot-preserving candidate ISOs."""
import argparse
import importlib.util
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, text=True)


def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(repo):
    result = []
    for p in sorted(repo.glob('*.deb')):
        if not re.fullmatch(r'[A-Za-z0-9_.+:%~-]+\.deb', p.name):
            raise ValueError(f'Unsafe package filename: {p.name}')
        name, version, arch = run('dpkg-deb', '-f', str(p), 'Package', 'Version', 'Architecture').splitlines()
        # dpkg-deb may label output when multiple fields are requested.
        name, version, arch = [s.split(': ', 1)[-1] for s in (name, version, arch)]
        if arch not in ('amd64', 'all'):
            raise ValueError(f'Unexpected package architecture: {arch}')
        result.append(dict(file=p.name, package=name, version=version, architecture=arch,
                           bytes=p.stat().st_size, sha256=digest(p)))
    if not result:
        raise ValueError('No .deb files supplied')
    keys = [x['package'] for x in result]
    if len(set(keys)) != len(keys):
        raise ValueError('More than one version of a package supplied')
    return result


def bundle(source):
    source = source.resolve(strict=True)
    destination = ROOT / 'offline/repo'
    if destination.exists():
        raise ValueError('offline/repo already exists; use a new checkout for a new bundle')
    records = inventory(source)
    required = [x.strip() for x in (ROOT / 'config/packages.txt').read_text().splitlines()
                if x.strip() and not x.lstrip().startswith('#')]
    available = {x['package'] for x in records}
    if set(required) - available:
        raise ValueError(f'Missing requested packages: {sorted(set(required) - available)}')
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        staged = Path(temp) / 'repo'
        staged.mkdir()
        for record in records:
            shutil.copy2(source / record['file'], staged / record['file'])
        (staged / 'Packages').write_text(run('dpkg-scanpackages', '.', '/dev/null', cwd=staged))
        (staged / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
        if (source / 'acquisition.txt').exists():
            shutil.copy2(source / 'acquisition.txt', staged / 'acquisition.txt')
        staged.rename(destination)
    print(f'Bundled {len(records)} packages in {destination}')


def workflow_inputs():
    spec = importlib.util.spec_from_file_location('editor_bundle', ROOT / 'scripts/editor.py')
    editor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(editor)
    extensions = editor.locked(ROOT / 'offline/editor')
    project = json.loads((ROOT / 'offline/workspace/manifest.json').read_text())
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', project['commit']):
        raise ValueError('Invalid project commit')
    if digest(ROOT / 'offline/workspace/ACLt.bundle') != project['sha256']:
        raise ValueError('ACLt seed changed after preparation')
    return extensions, project


def replace_extracted_text(path, content):
    # ISO files retain read-only permissions on extraction; replace our temporary copy.
    replacement = path.with_name(path.name + '.edited')
    replacement.write_text(content)
    replacement.chmod(path.stat().st_mode & 0o777)
    replacement.replace(path)


def customize_boot(original):
    if '/casper/vmlinuz' not in original or '/casper/initrd' not in original:
        raise ValueError('Unexpected base GRUB configuration')
    # Keep the original entries as fallback, and retain all interactive installation questions.
    entry = ('set default=0\nmenuentry "Install ZeroMatrix Development (offline setup)" {\n'
             '    set gfxpayload=keep\n'
             '    linux /casper/vmlinuz autoinstall subiquity.autoinstallpath=cdrom/zeromatrix/autoinstall.yaml --- quiet splash\n'
             '    initrd /casper/initrd\n}\n')
    return entry + original


def build(args):
    base = args.base.resolve(strict=True)
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.+-]*', args.version):
        raise ValueError('Invalid release version')
    if not re.fullmatch(r'[0-9a-fA-F]{64}', args.sha256) or digest(base) != args.sha256.lower():
        raise ValueError('Base ISO SHA256 mismatch')
    repo = ROOT / 'offline/repo'
    records = inventory(repo)
    if records != json.loads((repo / 'manifest.json').read_text()):
        raise ValueError('Offline bundle changed since preparation')
    extensions, project = workflow_inputs()
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    output = dist / f'zeromatrix-{args.version}-amd64.iso'
    if output.exists():
        raise ValueError('Output ISO already exists')
    partial = output.with_suffix(output.suffix + '.partial')
    if partial.exists():
        raise ValueError('Previous partial ISO exists; preserve its evidence and use a new version')
    try:
        commit = run('git', '-C', str(ROOT), 'rev-parse', 'HEAD').strip()
        status = run('git', '-C', str(ROOT), 'status', '--porcelain')
    except subprocess.CalledProcessError:
        commit, status = None, 'not a Git checkout'
    with tempfile.TemporaryDirectory(prefix='zeromatrix-') as temp:
        directory = Path(temp)
        payload = directory / 'zeromatrix'
        payload.mkdir()
        shutil.copytree(repo, payload / 'repo')
        shutil.copytree(ROOT / 'offline/editor', payload / 'editor')
        if (ROOT / 'offline/trust').exists():
            shutil.copytree(ROOT / 'offline/trust', payload / 'trust')
        shutil.copytree(ROOT / 'offline/workspace', payload / 'project')
        shutil.copytree(ROOT / 'scripts', payload / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT / 'config', payload / 'config')
        shutil.copytree(ROOT / 'templates', payload / 'templates')
        shutil.copy2(ROOT / 'config/autoinstall.yaml', payload / 'autoinstall.yaml')
        (payload / 'repo/Packages').write_text(run('dpkg-scanpackages', '.', '/dev/null', cwd=payload / 'repo'))
        for script in ('provision.sh', 'verify.sh'):
            shutil.copy2(ROOT / 'scripts' / script, payload / script)
        shutil.copy2(ROOT / 'config/baseline.json', payload / 'baseline.json')
        required = [x.strip() for x in (ROOT / 'config/packages.txt').read_text().splitlines()
                    if x.strip() and not x.lstrip().startswith('#')]
        versions = {x['package']: x['version'] for x in records}
        if set(required) - versions.keys():
            raise ValueError('Bundle does not cover current package configuration')
        (payload / 'install-specs.txt').write_text(''.join(f'{p}={v}\n' for p, v in sorted(versions.items())))
        source_hashes = {str(p.relative_to(ROOT)): digest(p) for folder in ('scripts', 'config', 'docs', 'templates', 'tests')
                         for p in sorted((ROOT / folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
        for filename in ('Makefile', 'VERSION', 'README.md', '.gitignore', '.gitattributes', '.editorconfig'):
            path = ROOT / filename
            if path.is_file():
                source_hashes[filename] = digest(path)
        manifest = dict(version=args.version, base_sha256=args.sha256.lower(), source_commit=commit,
                        source_status=status, source_files=source_hashes,
                        packages=records, extensions=extensions, project=project, acceptance='pending', distribution_scope='internal-company', license='undecided')
        (payload / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        files = sorted(p for p in payload.rglob('*') if p.is_file())
        (payload / 'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.relative_to(payload)}\n' for p in files))
        grubfile = directory / 'grub.cfg'
        run('xorriso', '-osirrox', 'on', '-indev', str(base), '-extract', '/boot/grub/grub.cfg', str(grubfile))
        replace_extracted_text(grubfile, customize_boot(grubfile.read_text()))
        md5file = directory / 'md5sum.txt'
        run('xorriso', '-osirrox', 'on', '-indev', str(base), '-extract', '/md5sum.txt', str(md5file))
        previous = md5file.read_text()
        if 'zeromatrix/' in previous:
            raise ValueError('Expected an uncustomized base ISO')
        previous = '\n'.join(line for line in previous.splitlines()
                             if line.strip() and line.split()[-1].lstrip('./') not in ('md5sum.txt', 'boot/grub/grub.cfg')) + '\n'
        files = sorted(p for p in payload.rglob('*') if p.is_file())
        replace_extracted_text(md5file, previous + f'{digest(grubfile, "md5")}  ./boot/grub/grub.cfg\n' + ''.join(f'{digest(p, "md5")}  ./zeromatrix/{p.relative_to(payload)}\n' for p in files))
        run('xorriso', '-indev', str(base), '-outdev', str(partial), '-boot_image', 'any', 'replay',
            '-map', str(grubfile), '/boot/grub/grub.cfg', '-map', str(payload), '/zeromatrix', '-map', str(md5file), '/md5sum.txt', '-commit')
    (dist / f'{output.name}.sha256').write_text(f'{digest(partial)}  {output.name}\n')
    (dist / f'{output.stem}.manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    partial.rename(output)
    print(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('bundle')
    prep.add_argument('source', type=Path)
    iso = sub.add_parser('build')
    iso.add_argument('--base', type=Path, required=True)
    iso.add_argument('--sha256', required=True)
    iso.add_argument('--version', required=True)
    args = parser.parse_args()
    if args.command == 'bundle':
        bundle(args.source)
    else:
        build(args)


if __name__ == '__main__':
    main()
