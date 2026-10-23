#!/bin/bash
# Supported GCE metadata startup-script, after reviewed host/disk preparation.
set -euo pipefail
root=/opt/remission-simulation
test "$(id -u)" = 0
/usr/bin/python3 "$root/prepare.py" --verify "$root"
source "$root/disk.env"
test -b "$DISK_DEVICE"
test "$(blkid -s UUID -o value "$DISK_DEVICE")" = "$DISK_UUID"
test "$(blkid -s TYPE -o value "$DISK_DEVICE")" = ext4
install -d -m 0755 /srv/remission
install -m 0644 "$root/srv-remission.mount" /etc/systemd/system/srv-remission.mount
systemctl daemon-reload
systemctl start srv-remission.mount
/usr/bin/python3 "$root/disk_guard.py"
docker compose version
docker compose --project-name remission-simulation --file "$root/compose.json" config --quiet
install -m 0644 "$root/remission-simulation.service" /etc/systemd/system/remission-simulation.service
systemctl daemon-reload
systemctl enable remission-simulation.service
systemctl start remission-simulation.service
