#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash scripts/install_local.sh <vendor-zip|inner-zip|vendor-dir>"
  exit 1
fi

INPUT=$(readlink -f "$1")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORKDIR=$(mktemp -d)
OUT_SRC=/usr/src/aic8800-ma14n-6.4.3.0-ma14n1
VENDOR_DIR=

cleanup() {
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

case "$INPUT" in
  *.zip)
    unzip -q "$INPUT" -d "$WORKDIR/unpacked"
    if [[ -f "$WORKDIR/unpacked/aic8800_linux_drvier.zip" ]]; then
      unzip -q "$WORKDIR/unpacked/aic8800_linux_drvier.zip" -d "$WORKDIR/vendor"
      VENDOR_DIR="$WORKDIR/vendor"
    else
      VENDOR_DIR="$WORKDIR/unpacked"
    fi
    ;;
  *)
    VENDOR_DIR="$INPUT"
    ;;
esac

python3 "$REPO_ROOT/scripts/prepare_dkms_tree.py" "$VENDOR_DIR" "$WORKDIR/dkms-src"

sudo apt-get update
sudo apt-get install -y dkms build-essential linux-headers-$(uname -r) patch unzip rsync

sudo rm -rf "$OUT_SRC"
sudo mkdir -p "$OUT_SRC"
sudo rsync -a "$WORKDIR/dkms-src/" "$OUT_SRC/"

if [[ -d "$VENDOR_DIR/aic8800_linux_drvier/fw/aic8800DC" ]]; then
  FW_SRC="$VENDOR_DIR/aic8800_linux_drvier/fw/aic8800DC"
elif [[ -d "$VENDOR_DIR/fw/aic8800DC" ]]; then
  FW_SRC="$VENDOR_DIR/fw/aic8800DC"
else
  echo "Could not find fw/aic8800DC in vendor package"
  exit 1
fi

sudo mkdir -p /lib/firmware/aic8800DC
sudo rsync -a "$FW_SRC/" /lib/firmware/aic8800DC/
sudo install -Dm644 "$REPO_ROOT/assets/80-aic8800-ma14n.rules" /etc/udev/rules.d/80-aic8800-ma14n.rules
sudo udevadm control --reload
sudo udevadm trigger || true
if [[ -L /dev/aicudisk ]]; then
  sudo eject /dev/aicudisk || true
fi

sudo dkms remove -m aic8800-ma14n -v 6.4.3.0-ma14n1 --all >/dev/null 2>&1 || true
sudo dkms add -m aic8800-ma14n -v 6.4.3.0-ma14n1
sudo dkms build -m aic8800-ma14n -v 6.4.3.0-ma14n1
# Force replacement is intentional here: this driver keeps the upstream/vendor
# module version string, so DKMS may otherwise refuse to overwrite an existing
# same-version module already present under /lib/modules.
sudo dkms install -m aic8800-ma14n -v 6.4.3.0-ma14n1 --force

sudo modprobe -r aic8800_fdrv aic_load_fw 2>/dev/null || true
sudo modprobe aic_load_fw || true
sudo modprobe aic8800_fdrv || true

echo
echo "Done. Useful checks:"
echo "  dkms status | grep aic8800-ma14n"
echo "  modinfo aic8800_fdrv | grep -i '2c4e.*0114'"
echo "  nmcli device status"
