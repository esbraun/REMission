#!/bin/bash
# First use ONLY; externally require matching new GCE disk/attachment IDs.
# Never invoke from startup/reboot/recovery. No execution before ROOTGO.
set -euo pipefail
DEVICE=/dev/disk/by-id/google-remission-data
sudo lsblk --paths --output NAME,SIZE,TYPE,FSTYPE,UUID,MOUNTPOINTS "$DEVICE"
test -b "$DEVICE"
SIGNATURES=$(sudo wipefs --no-act --noheadings --output TYPE "$DEVICE")
test -z "$SIGNATURES"
test "$(lsblk --noheadings --output TYPE "$DEVICE" | wc -l)" -eq 1
test "$(lsblk --noheadings --output TYPE "$DEVICE" | tr -d '[:space:]')" = disk
test -z "$(lsblk --noheadings --output MOUNTPOINTS "$DEVICE" | tr -d '[:space:]')"
sudo mkfs.ext4 -m 0 "$DEVICE"
sudo install -d -m 0755 /srv/remission
sudo mount -o nodev,nosuid "$DEVICE" /srv/remission
sudo blkid -s UUID -o value "$DEVICE"
sudo install -d -o 10001 -g 10001 -m 0700 /srv/remission/data /srv/remission/bootstrap /srv/remission/exports
sudo install -d -o root -g root -m 0700 /srv/remission/proxy-data /srv/remission/proxy-config
