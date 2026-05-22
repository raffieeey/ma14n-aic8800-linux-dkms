# Root cause notes

This repo exists because the Mercusys MA14N / AIC8800 vendor driver was not cleanly usable for me on Ubuntu 24.04 with kernel `6.17.0-29-generic`.

## Working IDs
- Temporary storage-like mode: `a69c:5721`
- Working Wi-Fi mode: `2c4e:0114`

## Main issues fixed

### 1. Mercusys `2c4e:0114` needed the DC path
In `aicwf_usb.c`, the vendor tree treated Mercusys `2c4e:0114` like the DW path. On my machine, it needed to follow the **AIC8800DC** path.

### 2. Probe cleanup path
In the same file, the unsupported-device path went to `out_free_bus`. On my setup that was riskier than failing early through `out_free`.

### 3. Timer compatibility on newer kernels
The driver needed compatibility for newer timer helpers:
- `from_timer(...)`
- `timer_delete()`
- `timer_delete_sync()`

### 4. cfg80211 helper signature changes
Newer kernels changed cfg80211 helper signatures, so the driver needed wrapper macros for:
- `cfg80211_rx_spurious_frame`
- `cfg80211_rx_unexpected_4addr_frame`

### 5. Linux 6.17 `radio_idx`
Linux 6.17 changed some cfg80211 op callbacks to include `radio_idx`, so the driver needed updated function signatures for:
- `rwnx_cfg80211_set_wiphy_params`
- `rwnx_cfg80211_set_tx_power`

## Why DKMS helps
Without DKMS, this kind of out-of-tree driver often breaks again at the next kernel upgrade.
With DKMS, the module source is registered under `/usr/src` and automatically rebuilt for newly installed kernels.
