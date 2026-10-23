#!/bin/bash
# Prepared stock commands from accepted packet; execute only after ROOTGO.
set -euo pipefail
test "$(dpkg --print-architecture)" = amd64
. /etc/os-release
test "$ID:$VERSION_CODENAME" = debian:bookworm
# Inspect conflicts; do not remove unrelated packages.
dpkg-query -W docker.io docker-compose docker-doc podman-docker containerd runc 2>/dev/null || true
for package in docker.io docker-compose podman-docker containerd runc; do
  package_state=$(dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null || true)
  if test "$package_state" = installed; then
    echo 'Conflicting preexisting package; preserve and stop.' >&2
    exit 1
  fi
done
test ! -e /opt/remission-simulation
sudo apt-get update
sudo apt-get install -y ca-certificates curl python3 e2fsprogs util-linux
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/debian' \
  'Suites: bookworm' 'Components: stable' 'Architectures: amd64' \
  'Signed-By: /etc/apt/keyrings/docker.asc' | sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null
sudo apt-get update
packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)
pinned=()
for package in "${packages[@]}"; do
  version=$(apt-cache policy "$package" | awk '/Candidate:/ {print $2}')
  test -n "$version" && test "$version" != '(none)'
  pinned+=("$package=$version")
done
printf '%s\n' "${pinned[@]}" > docker-package-selection.txt
sudo apt-get install -y "${pinned[@]}"
sudo apt-mark hold "${packages[@]}"
dpkg-query -W python3 e2fsprogs util-linux "${packages[@]}" > host-package-versions.txt
test -x /usr/bin/docker
sudo docker version
sudo docker compose version
python3 --version
test "$(sudo docker info --format '{{.LiveRestoreEnabled}}')" = false
HELPER_SHA256=9e676f2233b93e763276101dd8530e634aebf5d31d5581f64e7ffa978aefa0d8
curl -fsSL https://github.com/GoogleCloudPlatform/docker-credential-gcr/releases/download/v2.1.29/docker-credential-gcr_linux_amd64-2.1.29.tar.gz -o helper.tar.gz
printf '%s  helper.tar.gz\n' "$HELPER_SHA256" | sha256sum -c -
tar -xzf helper.tar.gz docker-credential-gcr
sudo install -m 0755 docker-credential-gcr /usr/bin/docker-credential-gcr
sudo docker-credential-gcr version
sudo docker-credential-gcr configure-docker --registries=us-central1-docker.pkg.dev
