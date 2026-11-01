#!/usr/bin/env python3
"""Pinned trust-store security updates and fail-closed image verification; no host installation."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PEM = r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----'


def policy(repo=ROOT):
    return json.loads((repo/'config/security-baseline.json').read_text())


def denied_roots(repo=ROOT):
    # DER bytes are needed to scan NSS builtins; the reviewed fingerprints gate the PEM file.
    baseline = policy(repo)
    ders = [ssl.PEM_cert_to_DER_cert(cert)
            for cert in re.findall(PEM, (repo/baseline['denied_roots_pem']).read_text(), re.S)]
    roots = {hashlib.sha256(der).hexdigest(): der for der in ders}
    if len(ders) != len(roots) or set(roots) != set(baseline['denied_root_sha256']):
        raise ValueError('Denied root certificates differ from reviewed fingerprints')
    return roots


def acquire(repo=ROOT):
    paths = []
    for record in policy(repo)['packages']:
        dest = repo/'build/security-inputs'/record['file']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest() != record['sha256']:
            partial = dest.with_suffix('.part')
            subprocess.run(['curl', '-fL', '--proto', '=https', '--proto-redir', '=https',
                            '--connect-timeout', '20', '--max-time', '300', record['url'], '-o', str(partial)], check=True)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Security package checksum mismatch: '+record['package'])
            partial.replace(dest)
        if dest.stat().st_size != record['bytes']:
            raise ValueError('Security package size mismatch: '+record['package'])
        paths.append(dest)
    return paths


def status_blocks(root, name):
    pattern = re.compile(r'^Package: '+re.escape(name)+'$', re.M)
    return [block for block in (root/'var/lib/dpkg/status').read_text().split('\n\n')
            if pattern.search(block) and re.search(r'^Status: install ok installed$', block, re.M)]


def package_status(root, name):
    for block in status_blocks(root, name):
        fields = dict(line.split(': ', 1) for line in block.splitlines()
                      if ': ' in line and not line.startswith(' '))
        return fields['Version'], block
    raise ValueError('Required security package missing: ' + name)


def effective(root, relative, lower=None):
    # The Live overlay hides lower-layer files it carries; otherwise the target file shows through.
    path = root/relative
    if lower is not None and not path.exists() and not path.is_symlink():
        path = Path(lower)/relative
    return path


def verify(root, repo=ROOT, lower=None):
    root = Path(root)
    baseline = policy(repo)
    denied = denied_roots(repo)
    versions = {}
    for record in baseline['packages']:
        version, _ = package_status(root, record['package'])
        if subprocess.run(['dpkg', '--compare-versions', version, 'ge', record['version']]).returncode:
            raise ValueError(record['package']+' predates '+record['advisory'])
        versions[record['package']] = version
    bundle = effective(root, 'etc/ssl/certs/ca-certificates.crt', lower)
    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError('Regular image-local CA bundle required')
    certs = re.findall(PEM, bundle.read_text(), re.S)
    if not certs:
        raise ValueError('Empty CA bundle')
    fingerprints = {hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert)).hexdigest() for cert in certs}
    if fingerprints.intersection(denied):
        raise ValueError('Distrusted eMudhra/emSign root remains in CA bundle')
    # NSS consumers (S/MIME, PDF signatures, xmlsec) read compiled-in roots, not the PEM bundle.
    builtins = effective(root, baseline['nss_builtins'], lower)
    if builtins.is_symlink() or not builtins.is_file():
        raise ValueError('Regular image-local NSS builtins library required')
    data = builtins.read_bytes()
    if any(der in data for der in denied.values()):
        raise ValueError('Distrusted eMudhra/emSign root remains in NSS builtins')
    return dict(packages=versions, bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(),
                certificates=len(certs), nss_builtins_sha256=hashlib.sha256(data).hexdigest())


def sync_live(root, live, name):
    """Copy a package's updated dpkg record, metadata and any shadowed files into the Live overlay."""
    blocks = [b.strip('\n') for b in status_blocks(root, name)]
    pattern = re.compile(r'^Package: '+re.escape(name)+'$', re.M)
    live_status = live/'var/lib/dpkg/status'
    kept = [b.strip('\n') for b in live_status.read_text().split('\n\n') if not pattern.search(b)]
    live_status.write_text('\n\n'.join([*filter(None, kept), *blocks])+'\n\n')
    info = root/'var/lib/dpkg/info'
    for source in [*info.glob(name+'.*'), *info.glob(name+':*.*')]:
        dest = live/'var/lib/dpkg/info'/source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest, follow_symlinks=False)
        if source.suffix != '.list':
            continue
        for line in source.read_text().splitlines():
            relative = line.lstrip('/')
            shadow = live/relative
            if relative and (shadow.is_file() or shadow.is_symlink()) and not (root/relative).is_dir():
                shadow.unlink()
                shutil.copy2(root/relative, shadow, follow_symlinks=False)


def update(root, live, work, repo=ROOT):
    records = policy(repo)['packages']
    staged = []
    try:
        for record in records:
            package = repo/'build/security-inputs'/record['file']
            if not package.is_file() or hashlib.sha256(package.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Run make security-inputs before building rootfs')
            target = root/'tmp'/record['file']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package, target)
            staged.append(target)
        subprocess.run(['chroot', str(root), 'env', 'DEBIAN_FRONTEND=noninteractive',
                        'dpkg', '-i', *['/tmp/'+record['file'] for record in records]], check=True)
        subprocess.run(['chroot', str(root), 'update-ca-certificates', '--fresh'], check=True)
    finally:
        for target in staged:
            target.unlink(missing_ok=True)
    # Live has an overriding dpkg database and may override the trust files too.
    for record in records:
        sync_live(root, live, record['package'])
    for relative in ('etc/ssl/certs', 'usr/share/ca-certificates', 'etc/ca-certificates.conf'):
        source, dest = root/relative, live/relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
        if source.is_dir():
            shutil.copytree(source, dest, symlinks=True)
        else:
            shutil.copy2(source, dest)
    evidence = dict(target=verify(root, repo), live=verify(live, repo, root), packages=records)
    (work/'security-verification.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'acquire':
        print('\n'.join(map(str, acquire())))
    elif len(sys.argv) in (2, 3):
        print(json.dumps(verify(Path(sys.argv[1]), lower=sys.argv[2] if len(sys.argv) == 3 else None), indent=2))
    else:
        raise SystemExit('usage: security_baseline.py acquire|ROOTFS [LOWER_ROOTFS]')
