#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo 'Run verification as a normal developer user' >&2; exit 1; }
out=${1:-"$HOME/.local/state/zeromatrix/$(date -u +%Y%m%dT%H%M%SZ)"}
[[ ! -e $out ]] || { echo 'Evidence directory exists' >&2; exit 1; }
mkdir -p "$out"
out=$(realpath "$out")
exec > >(tee "$out/verify.log") 2>&1
trap 'rc=$?; printf "%s\n" "$rc" > "$out/exit-code"; echo "verify exit=$rc"' EXIT
cat /etc/os-release
uname -srmo
for tool in git g++ rustc cargo python3 bash sha256sum code; do command -v "$tool"; "$tool" --version; done
rustc --version --verbose
dpkg-query -W git g++ rustc cargo python3 bash coreutils code rust-src
cp /etc/zeromatrix/baseline.json "$out/baseline.json"
cat > "$out/smoke.cpp" <<'CPP'
#include <iostream>
#include <memory>
int main() { auto x = std::make_unique<int>(42); std::cout << *x << '\n'; }
CPP
g++ -std=c++17 -O2 -Wall -Wextra -Werror "$out/smoke.cpp" -o "$out/cpp-smoke"
"$out/cpp-smoke"
g++ -std=c++17 -g -fsanitize=address,undefined -fno-omit-frame-pointer "$out/smoke.cpp" -o "$out/sanitizer-smoke"
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 "$out/sanitizer-smoke"
mkdir "$out/rust-smoke"
cd "$out/rust-smoke"
cargo init --bin --edition 2021 --name zeromatrix_smoke .
cargo build --offline
cargo run --offline
python3 -c 'import fcntl, subprocess, tempfile; print("Python standard library smoke OK")'
echo 'Toolchain smoke checks passed. Compare recorded versions with ENV-1 and run ACLt full acceptance separately.'

python3 /opt/zeromatrix/offline/scripts/user-setup.py
profile="$HOME/.local/share/zeromatrix/vscode"
code --user-data-dir "$profile/data" --extensions-dir "$profile/extensions" --list-extensions --show-versions
echo 'Pinned editor extensions initialized; validate F5 and language services in the desktop session.'
