# HP ProDesk 600 G5 Mini — Intel UHD 630 iGPU Passthrough to LG TV

## Hardware

| Component | Detail |
|-----------|--------|
| Host | HP ProDesk 600 G5 Desktop Mini |
| CPU | Intel Core i7-9700T (Coffee Lake) |
| GPU | Intel UHD Graphics 630 (PCI 8086:3e98, rev 02) |
| Subsystem | Hewlett-Packard 103c:8598 |
| RAM | 32 GB |
| Storage | NVMe (ZFS root) |
| Display | LG Electronics LG TV SSCR2 (3840×2160 @ 60Hz) |
| TV IP | 192.168.1.110 (port 3000 open — Moonlight) |
| VM | VM 111 (ubuntu), IP 192.168.1.174, 8 GB RAM, 4 cores |

## Boot Configuration

Unlike traditional PVE installs, this system uses **ZFS root with UEFI boot**. Boot parameters are read from:

```
/etc/kernel/cmdline
```

NOT `/etc/default/grub`. The bootloader is refreshed with:

```bash
proxmox-boot-tool refresh
```

The active `/etc/kernel/cmdline` after configuration:

```
root=ZFS=rpool/ROOT/pve-1 boot=zfs intel_iommu=on iommu=pt zswap.enabled=1 zswap.compressor=lz4 zswap.max_pool_percent=30 vfio-pci.ids=8086:3e98
```

## Modprobe Config

```bash
# /etc/modprobe.d/vfio.conf
options vfio-pci ids=8086:3e98

# /etc/modprobe.d/blacklist-igpu.conf
blacklist i915
```

After updating modprobe config, run: `update-initramfs -u -k all`
This also auto-triggers `proxmox-boot-tool refresh`.

## VM 111 Configuration

```
hostpci0: 00:02.0,pcie=1,x-vga=1
vga: none
audio0: was removed (emulated ICH9 didn't help with HDMI audio)
bios: ovmf
machine: q35
```

The VM uses OVMF (UEFI) firmware with pre-enrolled keys and a 4M EFI disk. The q35 chipset provides proper PCIe topology support for GPU passthrough.

**Removed emulated audio**: `qm set 111 -delete audio0` — the emulated ICH9 HDA controller (`device=ich9-intel-hda,driver=none`) was removed because it doesn't carry HDMI audio and its presence doesn't help with GPU audio passthrough.

## Verification Inside VM

```bash
# GPU detected
$ lspci -nn | grep 8086:3e98
01:00.0 VGA compatible controller: Intel CoffeeLake-S GT2 [UHD Graphics 630]

# Driver bound
$ lspci -nnk -s 01:00.0 | grep "Kernel driver"
Kernel driver in use: i915

# DRM devices available
$ ls /dev/dri/
card0  by-path  renderD128

# Display connectors detected
$ ls /sys/class/drm/
card0  card0-DP-1  card0-DP-2  card0-DP-3  card0-HDMI-A-1  card0-HDMI-A-2  card0-HDMI-A-3  renderD128  version

# HDMI ports all show "disconnected"
# DP-3 shows "connected" with LG TV EDID (this is the physical HDMI port, detected as DP-3)
cat /sys/class/drm/card0-DP-3/status
# → connected
cat /sys/class/drm/card0-DP-3/modes
# → 3840x2160, 4096x2160, 1920x1080, etc.
```

## Display Manager

- **GNOME Display Manager** (GDM) running
- **Wayland** session (not X11)
- User `leo` auto-logged in
- TV detected at **3840×2160 @ 60Hz** (preferred mode)
- Display configured automatically via EDID — no manual `xrandr` or Wayland config needed

## Wayland Scaling for 4K TV

On a 4K TV at typical viewing distance, 100% scaling makes UI elements too small. The fix:

```bash
# Inside the VM, as the desktop user:
gsettings set org.gnome.mutter experimental-features "['scale-monitor-framebuffer']"
gsettings set org.gnome.desktop.interface text-scaling-factor 2.0
gsettings set org.gnome.desktop.interface scaling-factor 0
```

- `scale-monitor-framebuffer` enables per-monitor fractional scaling in Wayland
- `text-scaling-factor 2.0` provides 200% scaling (effectively 1080p-equivalent UI on a 4K display)
- `scaling-factor 0` leaves it to auto/manual per-monitor config

The user can also configure this in GNOME Settings → Displays → Scale.

## USB Peripheral Passthrough

For keyboard and mouse, pass through individual USB devices by vendor:product ID (not by bus-port, which changes on reboot):

```bash
# From PVE host — add to VM
qm set 111 -usb2 host=1a2c:2124    # SEM USB Keyboard
qm set 111 -usb3 host=1a86:e30a    # QinHeng USB Composite Device (mouse)
```

**Device details on this system:**

| Device | ID | Role | Notes |
|--------|----|------|-------|
| SEM USB Keyboard | `1a2c:2124` | Keyboard | Two HID interfaces |
| QinHeng Composite | `1a86:e30a` | Mouse | Interface 0=keyboard, Interface 1=mouse |
| Intel Bluetooth | `8087:0aaa` | Bluetooth | Already passed as `usb0`, needs firmware in VM |

**Key points:**
- The QinHeng composite device has TWO HID interfaces — the mouse is on interface 1
- Passing by `host=ID:ID` is preferred over `host=bus-port` because bus-port changes on reboot
- Verify with: `lsusb` and `cat /proc/bus/input/devices | grep -E 'Mouse|Keyboard'` inside the VM
- The QEMU XHCI controller (`07:1b.0`) handles the passed-through USB devices

## HDMI Audio Limitation

**HDMI audio is NOT available** via VFIO passthrough on this hardware.

### Root cause

Coffee Lake (CFL) UHD 630 does **not** expose a separate PCI audio function. On the host:

```bash
lspci -nn -s 00:02
00:02.0 VGA compatible controller [0300]: Intel Corporation CoffeeLake-S GT2 [UHD Graphics 630] [8086:3e98] (rev 02)
# No 00:02.1 — the audio function does not exist as a separate PCI device
```

Inside the VM, `lspci -nn -s 01:00.1` shows an empty slot — no vendor/device ID, no driver can bind. The `snd_hda_intel` driver cannot attach to it. No `audio_auto` file exists under `/sys/class/drm/card0-*` connectors.

### Practical solutions

| Option | Cost | Quality | Notes |
|--------|------|---------|-------|
| USB → 3.5mm audio adapter | ~$10-15 | Good | Plug into HP ProDesk, pass through via `host=ID:ID`, connect to TV/speakers via 3.5mm |
| HDMI audio extractor | ~$15-25 | Excellent | Splits HDMI into video+audio, audio goes to USB adapter → VM |
| Bluetooth audio (if BT works) | $0 | Variable | Intel BT adapter (8087:0aaa) passed through; needs firmware `ibt-11-5.sfi` in VM |
| ProDesk 3.5mm jack via cAVS | $0 | Good | Pass through host audio controller `00:1f.3` to VM; analog only |

## Key Lessons

1. **Kernel cmdline location**: `/etc/kernel/cmdline` (not GRUB) on ZFS-root PVE installs
2. **Proxmox boot tool**: `proxmox-boot-tool refresh` is the correct way to apply cmdline changes
3. **update-initramfs triggers proxmox-boot-tool**: Running `update-initramfs -u -k all` automatically runs the zz-proxmox-boot hook
4. **VM power cycle**: The VM must be fully stopped and started (not just rebooted) for `hostpci0` changes to take effect
5. **Display mapping**: The physical HDMI port on the HP Mini may appear as DP-3 in the Intel GPU's connector list — test all connectors with status checks
6. **Proxmox loses local video**: Only acceptable if SSH/WebUI access is available for recovery
7. **No HDMI audio from Coffee Lake iGPU VFIO passthrough**: The audio function doesn't exist as a separate PCI device; use USB audio or Bluetooth as workaround
8. **USB device passthrough by ID**: Use `host=VENDOR:PRODUCT` format, not `host=bus-port` — IDs are stable across reboots
