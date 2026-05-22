#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path

VERSION = "6.4.3.0-ma14n1"
PACKAGE = "aic8800-ma14n"

DKMS_CONF = f'''PACKAGE_NAME="{PACKAGE}"
PACKAGE_VERSION="{VERSION}"
BUILT_MODULE_NAME[0]="aic_load_fw"
BUILT_MODULE_LOCATION[0]="aic_load_fw"
DEST_MODULE_LOCATION[0]="/kernel/drivers/net/wireless/aic8800"
BUILT_MODULE_NAME[1]="aic8800_fdrv"
BUILT_MODULE_LOCATION[1]="aic8800_fdrv"
DEST_MODULE_LOCATION[1]="/kernel/drivers/net/wireless/aic8800"
AUTOINSTALL="yes"
MAKE[0]="make -j$(nproc)"
CLEAN="make clean"
'''


def find_vendor_root(src: Path) -> Path:
    if (src / 'drivers' / 'aic8800').is_dir():
        return src
    if (src / 'aic8800_linux_drvier' / 'drivers' / 'aic8800').is_dir():
        return src / 'aic8800_linux_drvier'
    raise SystemExit(f'Could not find vendor root under {src}')


def replace_once(path: Path, old: str, new: str):
    text = path.read_text()
    if old not in text:
        raise SystemExit(f'Expected text not found in {path}: {old!r}')
    path.write_text(text.replace(old, new, 1))


def apply_local_patches(out: Path):
    usb = out / 'aic8800_fdrv' / 'aicwf_usb.c'
    replace_once(
        usb,
        '\t}else if(pid == USB_PRODUCT_ID_AIC8800DC){\n',
        '\t}else if(pid == USB_PRODUCT_ID_AIC8800DC\n\t        || (vid == USB_VENDOR_ID_MERCUSYS && pid == USB_PRODUCT_ID_MERCUSYS)){\n',
    )
    replace_once(
        usb,
        '        || (vid == USB_VENDOR_ID_MERCUSYS && pid == USB_PRODUCT_ID_MERCUSYS)\n',
        '',
    )
    replace_once(
        usb,
        '        AICWFDBG(LOGERROR, "%s pid:0x%04X vid:0x%04X unsupport\\n", \n',
        '        AICWFDBG(LOGERROR, "%s vid:0x%04X pid:0x%04X unsupport\\n", \n',
    )
    replace_once(usb, '        goto out_free_bus;\n', '        goto out_free;\n')

    compat = out / 'aic8800_fdrv' / 'rwnx_compat.h'
    replace_once(
        compat,
        '#include <linux/version.h>\n',
        '#include <linux/version.h>\n\n#ifndef from_timer\n#define from_timer(var, callback_timer, timer_field) \\\n    container_of(callback_timer, typeof(*var), timer_field)\n#endif\n\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 15, 0)\n#ifndef del_timer_sync\n#define del_timer_sync(timer) timer_delete_sync(timer)\n#endif\n#ifndef del_timer\n#define del_timer(timer) timer_delete(timer)\n#endif\n#endif\n',
    )
    replace_once(
        compat,
        '#endif\n\n#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 9, 0)\n',
        '#endif\n\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 12, 0)\n#define cfg80211_rx_spurious_frame(dev, addr, gfp) \\\n    cfg80211_rx_spurious_frame(dev, addr, -1, gfp)\n#define cfg80211_rx_unexpected_4addr_frame(dev, addr, gfp) \\\n    cfg80211_rx_unexpected_4addr_frame(dev, addr, -1, gfp)\n#endif\n\n#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 9, 0)\n',
    )

    defs = out / 'aic8800_fdrv' / 'rwnx_defs.h'
    replace_once(defs, '#include <linux/skbuff.h>\n', '#include <linux/skbuff.h>\n#include <linux/timer.h>\n')

    mainc = out / 'aic8800_fdrv' / 'rwnx_main.c'
    replace_once(
        mainc,
        'static int rwnx_cfg80211_set_wiphy_params(struct wiphy *wiphy, u32 changed)\n{\n',
        'static int rwnx_cfg80211_set_wiphy_params(struct wiphy *wiphy,\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 17, 0)\n                                          int radio_idx,\n#endif\n                                          u32 changed)\n{\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 17, 0)\n    (void)radio_idx;\n#endif\n',
    )
    replace_once(
        mainc,
        '#if LINUX_VERSION_CODE >= KERNEL_VERSION(3, 8, 0)\n struct wireless_dev *wdev,\n#endif\n                                      enum nl80211_tx_power_setting type, int mbm)\n{\n    #if LINUX_VERSION_CODE < KERNEL_VERSION(3, 8, 0)\n    struct wireless_dev *wdev = NULL;\n    #endif\n',
        '#if LINUX_VERSION_CODE >= KERNEL_VERSION(3, 8, 0)\n struct wireless_dev *wdev,\n#endif\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 17, 0)\n                                      int radio_idx,\n#endif\n                                      enum nl80211_tx_power_setting type, int mbm)\n{\n    #if LINUX_VERSION_CODE < KERNEL_VERSION(3, 8, 0)\n    struct wireless_dev *wdev = NULL;\n    #endif\n#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 17, 0)\n    (void)radio_idx;\n#endif\n',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vendor_dir', help='Extracted vendor directory containing drivers/aic8800 and fw/aic8800DC')
    ap.add_argument('output_dir', help='Where to create the patched DKMS-ready source tree')
    args = ap.parse_args()

    vendor_root = find_vendor_root(Path(args.vendor_dir).resolve())
    out = Path(args.output_dir).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    src = vendor_root / 'drivers' / 'aic8800'
    shutil.copytree(src, out, dirs_exist_ok=True)
    apply_local_patches(out)
    (out / 'dkms.conf').write_text(DKMS_CONF)
    print(f'Wrote DKMS source tree to {out}')


if __name__ == '__main__':
    main()
