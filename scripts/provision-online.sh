#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]]
media=$(realpath -- "${1:?payload required}")
(cd "$media" && sha256sum --strict -c SHA256SUMS)
install -d /opt/zeromatrix /var/log/zeromatrix /etc/zeromatrix
if [[ $media != /opt/zeromatrix/offline ]]; then cp -a "$media" /opt/zeromatrix/offline; fi
payload=/opt/zeromatrix/offline
exec > >(tee -a /var/log/zeromatrix/provision.log) 2>&1
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=3 update
mapfile -t packages < "$payload/install-specs.txt"
apt-get -y install "${packages[@]}"
# Official Microsoft repository: authenticated APT, scoped signing key.
curl --fail --location --retry 3 https://packages.microsoft.com/keys/microsoft.asc -o /tmp/zeromatrix-microsoft.asc
gpg --batch --yes --dearmor -o /usr/share/keyrings/zeromatrix-microsoft.gpg /tmp/zeromatrix-microsoft.asc
chmod 644 /usr/share/keyrings/zeromatrix-microsoft.gpg
printf '%s\n' 'deb [arch=amd64 signed-by=/usr/share/keyrings/zeromatrix-microsoft.gpg] https://packages.microsoft.com/repos/code stable main' > /etc/apt/sources.list.d/zeromatrix-code.list
printf 'code code/add-microsoft-repo boolean false\n' | debconf-set-selections
apt-get -o Acquire::Retries=3 update
apt-get -y install code
install -m 644 "$payload/baseline.json" /etc/zeromatrix/baseline.json
install -m 755 "$payload/scripts/zeromatrix-code" "$payload/scripts/zeromatrix-first-login" /usr/local/bin/
install -d /usr/share/applications /etc/xdg/autostart
install -m 644 "$payload/templates/desktop/zeromatrix.desktop" /usr/share/applications/
install -m 644 "$payload/templates/desktop/zeromatrix-first-login.desktop" /etc/xdg/autostart/
dpkg-query -W > /var/log/zeromatrix/installed-packages.tsv
