#!/usr/bin/env python3
"""Initialize the user's isolated editor profile and offline workspace once."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

PAYLOAD = Path('/opt/zeromatrix/offline')


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def seed_project(payload, workspace):
    record = json.loads((payload / 'project/manifest.json').read_text())
    destination = workspace / 'ACLt'
    if destination.exists():
        if not (destination / '.git').exists():
            raise ValueError('Existing ACLt directory is not a Git checkout; it will not be overwritten')
        return
    with tempfile.TemporaryDirectory(prefix='.aclt-seed-', dir=workspace) as t:
        project = Path(t) / 'ACLt'
        project.mkdir()
        run('git', 'init', str(project))
        run('git', '-C', str(project), 'fetch', record.get('url') or str(payload / 'project/ACLt.bundle'), record['commit'] if record.get('url') else 'HEAD')
        if record.get('url'):
            run('git', '-C', str(project), 'remote', 'add', 'origin', record['url'])
        run('git', '-C', str(project), 'checkout', '-b', 'dev/local', record['commit'])
        project.rename(destination)


def setup(payload=PAYLOAD, home=None):
    if os.geteuid() == 0:
        raise ValueError('User initialization must run as the developer, never root')
    home = Path.home() if home is None else Path(home)
    state = home / '.local/state/zeromatrix'
    state.mkdir(parents=True, exist_ok=True)
    with (state / 'setup.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if (state / 'setup-complete').exists():
            return
        run('sha256sum', '--strict', '-c', 'SHA256SUMS', cwd=payload)
        workspace = home / 'workspace/ZeroMatrixTech'
        workspace.mkdir(parents=True, exist_ok=True)
        # Merge template files without overwriting the user's existing work.
        shutil.copytree(payload / 'templates/workspace', workspace, dirs_exist_ok=True,
                        copy_function=lambda a, b: shutil.copy2(a, b) if not Path(b).exists() else b)
        seed_project(payload, workspace)
        profile = home / '.local/share/zeromatrix/vscode'
        settings = profile / 'data/User/settings.json'
        settings.parent.mkdir(parents=True, exist_ok=True)
        defaults = json.loads((payload / 'config/vscode/settings.json').read_text())
        if settings.exists():
            existing = json.loads(settings.read_text())
            defaults.update(existing)
        settings.write_text(json.dumps(defaults, indent=2) + '\n')
        (profile / 'extensions').mkdir(parents=True, exist_ok=True)
        records = json.loads((payload / 'editor/manifest.json').read_text())
        for record in records:
            run('/usr/bin/code', '--user-data-dir', str(profile / 'data'),
                '--extensions-dir', str(profile / 'extensions'), '--install-extension',
                (record['id'] + '@' + record['version']) if record.get('online') else str(payload / 'editor' / record['file']), '--force', '--do-not-include-pack-dependencies')
        python = workspace / 'python/.venv/bin/python'
        if not python.exists():
            run('/usr/bin/python3', '-m', 'venv', str(workspace / 'python/.venv'))
        installed = subprocess.check_output(['/usr/bin/code', '--user-data-dir', str(profile / 'data'),
                        '--extensions-dir', str(profile / 'extensions'), '--list-extensions',
                        '--show-versions'], text=True)
        (state / 'extensions.txt').write_text(installed)
        actual = {line.strip().lower() for line in installed.splitlines()}
        missing = [r['id'] for r in records if (r['id'] + '@' + r['version']).lower() not in actual]
        if missing:
            raise ValueError('Extension installation did not match manifest: ' + ', '.join(missing))
        (state / 'setup-complete').write_text((payload / 'manifest.json').read_text())


if __name__ == '__main__':
    setup()
