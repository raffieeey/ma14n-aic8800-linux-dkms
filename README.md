# Mercusys MA14N / AIC8800 Linux DKMS helper

I experienced this issue myself on Ubuntu 24.04 with a Mercusys MA14N / AIC8800 USB adapter, so I cleaned up the workaround and put it here.

**Hope it helps you.**

## Disclaimer
This repo is shared in good faith and **use is entirely at your own risk**. I am **not liable for any future problems**, breakage, boot issues, kernel regressions, network loss, data loss, or other damage that may happen from using these scripts, patches, or instructions.

## What this repo is
This repository contains:
- kernel compatibility patches for the vendor AIC8800 driver
- a DKMS packaging helper so the driver can rebuild automatically after kernel updates
- a local install script that patches the vendor package on your own machine and installs it via DKMS
- the USB mode-switch udev rule needed for the temporary `Aic MSC` storage mode

## What this repo does **not** include
To stay on the safe side legally, this repo does **not** ship:
- the vendor driver source tarball/zip
- firmware binaries

You need to download the vendor package yourself and point the installer at it.

## Tested environment
- Adapter: Mercusys MA14N
- Working Wi-Fi USB ID: `2c4e:0114`
- Temporary storage-mode ID seen in the vendor rule path: `a69c:5721`
- Distro: Ubuntu 24.04
- Kernel tested: `6.17.0-29-generic`

## Symptoms this may help with
- MA14N appears in `lsusb` but no stable Wi-Fi interface shows up
- the machine becomes unstable when the vendor module probes
- the vendor tree builds poorly or not at all on newer kernels
- the adapter re-enumerates oddly after showing up as a storage device first
- driver works once but breaks after a kernel update

## Root cause summary
The main issues I hit were:
- Mercusys `2c4e:0114` needed to follow the **AIC8800DC** path instead of the DW path
- a probe failure path in `aicwf_usb.c` needed to fail through `out_free` instead of `out_free_bus`
- newer kernels needed timer compatibility helpers (`from_timer`, `timer_delete`, `timer_delete_sync`)
- newer cfg80211 APIs needed compatibility shims
- Linux 6.17 changed cfg80211 callback signatures to include `radio_idx`

## Repo layout
- `patches/0001-mercusys-ma14n-dc-path-and-probe-fix.patch`
- `patches/0002-linux-6.17-compat.patch`
- `scripts/prepare_dkms_tree.py`
- `scripts/install_local.sh`
- `assets/80-aic8800-ma14n.rules`
- `docs/root-cause.md`

## Install flow
1. Download the vendor package yourself.
2. Install prerequisites and DKMS.
3. Let the script extract/patch/package the driver locally.
4. DKMS registers the source under `/usr/src/` and builds modules for your kernel.
5. Firmware and the udev mode-switch rule are installed from your local vendor package.

### Example
```bash
bash scripts/install_local.sh ~/Downloads/MA14N\(EU\)_V1_Linux_Beta20251013080153.zip
```

The script also accepts:
- the inner vendor zip (`aic8800_linux_drvier.zip`)
- an already-extracted vendor directory like `aic8800_linux_drvier/`

## After install
Useful checks:
```bash
dkms status | grep aic8800-ma14n
modinfo aic8800_fdrv | grep -i '2c4e.*0114'
lsmod | grep aic
nmcli device status
journalctl -b | grep -i aic
```

## DKMS package name
- Package name: `aic8800-ma14n`
- Package version: `6.4.3.0-ma14n1`

## Notes
- This was tested on one machine and one adapter family. If your hardware or kernel is different, you may need additional fixes.
- If you already have a working network adapter, keep it connected while testing this one.
- Firmware still comes from the vendor package you downloaded locally.

## Credits
Credits to the original vendor/AICSemi/RivieraWaves driver authors for the underlying driver code. This repo only documents and automates a local patch-and-package workflow around that vendor release.
