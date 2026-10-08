#!/usr/bin/env python3
"""Export a clean ACLt commit as an offline Git bundle, without local settings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def bundle(source):
    source = source.resolve(strict=True)
    for required in ('scripts/run-singlehost.sh', 'scripts/aclt-flow.py'):
        if not (source / required).is_file():
            raise ValueError(f'Not an ACLt checkout: missing {required}')
    if run('git', '-C', str(source), 'status', '--porcelain'):
        raise ValueError('ACLt checkout has uncommitted changes; export an reviewed clean commit')
    commit = run('git', '-C', str(source), 'rev-parse', 'HEAD')
    destination = ROOT / 'offline/workspace'
    if destination.exists():
        raise ValueError('offline/workspace exists; use a new checkout for the next seed')
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as t:
        staged = Path(t) / 'workspace'
        staged.mkdir()
        seed = staged / 'ACLt.bundle'
        run('git', '-C', str(source), 'bundle', 'create', str(seed), 'HEAD')
        record = dict(project='ACLt', commit=commit, file='ACLt.bundle',
                      sha256=hashlib.sha256(seed.read_bytes()).hexdigest(), working_tree='clean')
        (staged / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
        staged.rename(destination)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    bundle(p.parse_args().source)
