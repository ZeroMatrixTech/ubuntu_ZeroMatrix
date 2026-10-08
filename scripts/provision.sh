#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo 'Root required' >&2; exit 1; }
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 26.04 && $(dpkg --print-architecture) == amd64 ]] || exit 1
media=$(realpath -- "${1:?payload directory required}")
(cd "$media" && sha256sum --strict -c SHA256SUMS)
install -d /opt/zeromatrix /etc/zeromatrix /var/lib/zeromatrix /var/log/zeromatrix
# Preserve an existing bundle; never silently replace a provisioned environment.
if [[ -e /opt/zeromatrix/offline ]]; then
  cmp "$media/SHA256SUMS" /opt/zeromatrix/offline/SHA256SUMS
else
  cp -a "$media" /opt/zeromatrix/offline
fi
payload=/opt/zeromatrix/offline
chmod -R a+rX "$payload"
exec > >(tee -a /var/log/zeromatrix/provision.log) 2>&1
trap 'rc=$?; echo "provision exit=$rc"' EXIT
work=$(mktemp -d /var/lib/zeromatrix/apt.XXXXXXXX)
chmod 755 "$work"
printf 'deb [trusted=yes] file:%s/repo ./
' "$payload" > "$work/sources.list"
mkdir -p "$work/lists/partial" "$work/archives/partial"
opts=(-o "Dir::Etc::sourcelist=$work/sources.list" -o 'Dir::Etc::sourceparts=-'
      -o "Dir::State::lists=$work/lists" -o "Dir::Cache::archives=$work/archives"
      -o 'APT::Get::List-Cleanup=0' -o 'Acquire::Retries=0')
apt-get "${opts[@]}" update
mapfile -t packages < "$payload/install-specs.txt"
printf 'code code/add-microsoft-repo boolean false\n' | debconf-set-selections
DEBIAN_FRONTEND=noninteractive apt-get "${opts[@]}" -y --no-install-recommends --no-remove install "${packages[@]}"
install -d /opt/zeromatrix/toolchains /etc/skel/workspace/ZeroMatrixTech
install -m 644 "$payload/baseline.json" /etc/zeromatrix/baseline.json
install -m 644 "$payload/manifest.json" /var/lib/zeromatrix/manifest.json
install -m 755 "$payload/scripts/zeromatrix-code" /usr/local/bin/zeromatrix-code
install -m 755 "$payload/scripts/zeromatrix-first-login" /usr/local/bin/zeromatrix-first-login
install -d /usr/share/applications /etc/xdg/autostart
install -m 644 "$payload/templates/desktop/zeromatrix.desktop" /usr/share/applications/zeromatrix.desktop
install -m 644 "$payload/templates/desktop/zeromatrix-first-login.desktop" /etc/xdg/autostart/zeromatrix-first-login.desktop
date -u +%FT%TZ > /var/lib/zeromatrix/provisioned-at
echo 'Offline provisioning complete; first login initializes the ZeroMatrix VS Code workspace.'
