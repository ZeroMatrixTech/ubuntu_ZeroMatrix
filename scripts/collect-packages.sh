#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Run as root in a disposable acquisition VM' >&2; exit 1; }
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 26.04 && $(dpkg --print-architecture) == amd64 ]] || exit 1
[[ $PRETTY_NAME == *26.04.1* ]] || { echo 'Expected Ubuntu 26.04.1' >&2; exit 1; }
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
code_deb=$(python3 "$root/scripts/code-input.py" path)
out=$(realpath -m -- "${1:?absolute output directory required}")
[[ ! -e $out ]] || { echo 'Output already exists' >&2; exit 1; }
mkdir -p "$out/partial"
mapfile -t packages < <(sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d; /^code$/d' "$root/config/packages.txt")
apt-get update
# Reinstall requested packages even if present; apt resolves dependencies with an empty package status so already installed dependencies are also downloaded.
apt-get -y --download-only --reinstall -o "Dir::Cache::archives=$out" -o Dir::State::status=/dev/null install "${packages[@]}" "$code_deb"
# Complete reverse dependencies against the acquisition VM's installed Desktop packages.
mapfile -t frozen < <(python3 - "$out" <<'LOCK'
from pathlib import Path
import subprocess, sys
for package in sorted(Path(sys.argv[1]).glob('*.deb')):
    name = subprocess.check_output(['dpkg-deb', '-f', str(package), 'Package'], text=True).strip()
    version = subprocess.check_output(['dpkg-deb', '-f', str(package), 'Version'], text=True).strip()
    if name != 'code':
        print(name + '=' + version)
LOCK
)
apt-get -y --download-only --no-install-recommends --no-remove -o "Dir::Cache::archives=$out" install "${frozen[@]}" "$code_deb"
cp -- "$code_deb" "$out/code_$(dpkg-deb -f "$code_deb" Version)_amd64.deb"
{ cat /etc/os-release; dpkg-deb -f "$code_deb" Package Version Architecture; sha256sum "$code_deb"; dpkg-query -W; apt-cache policy "${packages[@]}"; } > "$out/acquisition.txt"
echo 'Downloaded candidate package set. A fresh offline installation must validate its dependency closure.'
