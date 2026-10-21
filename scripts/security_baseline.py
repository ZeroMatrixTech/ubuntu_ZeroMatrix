#!/usr/bin/env python3
"""Pinned CA security update and fail-closed image verification; no host installation."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def policy(repo=ROOT):
    return json.loads((repo/'config/security-baseline.json').read_text())


def acquire(repo=ROOT):
    record = policy(repo)['package']
    dest = repo/'build/security-inputs'/record['file']
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or hashlib.sha256(dest.read_bytes()).hexdigest() != record['sha256']:
        partial = dest.with_suffix('.part')
        subprocess.run(['curl', '-fL', '--proto', '=https', '--proto-redir', '=https',
                        '--connect-timeout', '20', '--max-time', '300', record['url'], '-o', str(partial)], check=True)
        if hashlib.sha256(partial.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('CA security package checksum mismatch')
        partial.replace(dest)
    if dest.stat().st_size != record['bytes']:
        raise ValueError('CA security package size mismatch')
    return dest


def package_status(root, name):
    for block in (root/'var/lib/dpkg/status').read_text().split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines()
                      if ': ' in line and not line.startswith(' '))
        if fields.get('Package') == name and fields.get('Status') == 'install ok installed':
            return fields['Version'], block
    raise ValueError('Required security package missing: ' + name)


def verify(root, repo=ROOT):
    root = Path(root)
    baseline = policy(repo)
    version, _ = package_status(root, 'ca-certificates')
    if subprocess.run(['dpkg', '--compare-versions', version, 'ge', baseline['minimum_ca_version']]).returncode:
        raise ValueError('CA package predates ' + baseline['advisory'])
    bundle = root/'etc/ssl/certs/ca-certificates.crt'
    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError('Regular image-local CA bundle required')
    certs = re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----', bundle.read_text(), re.S)
    if not certs:
        raise ValueError('Empty CA bundle')
    fingerprints = {hashlib.sha256(ssl.PEM_cert_to_DER_cert(cert)).hexdigest() for cert in certs}
    if fingerprints.intersection(baseline['denied_root_sha256']):
        raise ValueError('Distrusted eMudhra/emSign root remains in CA bundle')
    return dict(advisory=baseline['advisory'], ca_version=version,
                bundle_sha256=hashlib.sha256(bundle.read_bytes()).hexdigest(), certificates=len(certs))


def update(root, live, work, repo=ROOT):
    record = policy(repo)['package']
    package = repo/'build/security-inputs'/record['file']
    if not package.is_file() or hashlib.sha256(package.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('Run make security-inputs before building rootfs')
    target = root/'tmp'/record['file']
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package, target)
    try:
        subprocess.run(['chroot', str(root), 'env', 'DEBIAN_FRONTEND=noninteractive',
                        'dpkg', '-i', '/tmp/'+record['file']], check=True)
        subprocess.run(['chroot', str(root), 'update-ca-certificates', '--fresh'], check=True)
    finally:
        target.unlink(missing_ok=True)
    # Live has an overriding dpkg database and may override the trust files too.
    _, ca_block = package_status(root, 'ca-certificates')
    live_status = live/'var/lib/dpkg/status'
    blocks = [b for b in live_status.read_text().split('\n\n')
              if not re.search(r'^Package: ca-certificates$', b, re.M)]
    live_status.write_text('\n\n'.join([*filter(None, blocks), ca_block])+'\n\n')
    for source in (root/'var/lib/dpkg/info').glob('ca-certificates.*'):
        dest = live/'var/lib/dpkg/info'/source.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest, follow_symlinks=False)
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
    evidence = dict(target=verify(root, repo), live=verify(live, repo), package=record)
    (work/'security-verification.json').write_text(json.dumps(evidence, indent=2)+'\n')


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'acquire':
        print(acquire())
    elif len(sys.argv) == 2:
        print(json.dumps(verify(Path(sys.argv[1])), indent=2))
    else:
        raise SystemExit('usage: security_baseline.py acquire|ROOTFS')
