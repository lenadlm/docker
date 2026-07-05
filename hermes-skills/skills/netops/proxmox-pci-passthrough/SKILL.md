---
name: proxmox-pci-passthrough
description: Class-level umbrella skill for passing through PCI devices (GPU, NVMe, USB controllers, NICs) from a Proxmox VE host to VMs using VFIO. Covers IOMMU setup, driver binding, VM configuration, ZFS-root boot param quirks, and verification steps.
version: 1.0.0
author: Hermes
metadata:
  hermes:
    tags: [proxmox, vfio, passthrough, gpu, pci, iommu]
    related_skills: [proxmox-api-health]
---

# Proxmox PCI Passthrough (Umbrella Skill)

## Purpose

Framework for passing through physical PCI devices (GPUs, NVMe drives, USB controllers, network cards) from a Proxmox VE host to a VM via VFIO. Covers the full lifecycle: IOMMU enablement → driver binding → VM config → verification → display output.

## Prerequisites

- Proxmox VE 8.x+ (verified on 9.x)
- Hardware with IOMMU support (Intel VT-d or AMD-Vi)
- CPU/chipset that supports independent IOMMU groups
- OVMF (UEFI) firmware for the target VM
- q35 machine type for the target VM

## Workflow

### 1. Enable IOMMU

**On PVE with ZFS root** (the default for most Proxmox installs):

Boot parameters go in `/etc/kernel/cmdline`, NOT `/etc/default/grub`.

```bash
# Edit the kernel cmdline
echo "root=ZFS=rpool/ROOT/pve-1 boot=zfs intel_iommu=on iommu=pt [other params] vfio-pci.ids=<PCI_VENDOR:DEVICE>" > /etc/kernel/cmdline

# Refresh the bootloader
proxmox-boot-tool refresh

# Reboot
reboot
```

**On PVE with GRUB (non-ZFS):**

```bash
# Edit /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"

# Apply
update-grub
reboot
```

- For AMD CPUs: use `amd_iommu=on iommu=pt` instead of `intel_iommu=on`
- `iommu=pt` enables passthrough mode (better performance, avoids IOMMU mapping overhead for host devices)
- `vfio-pci.ids=8086:3e98` pre-binds the specified PCI device to vfio-pci at boot

### 2. Find the PCI Device

```bash
lspci -nn | grep -iE "vga|display|3d|nvme|usb|network"
```

Note the PCI address (e.g., `00:02.0`) and vendor:device ID (e.g., `8086:3e98`).

### 3. Bind Device to VFIO

**Method A** (recommended — via kernel cmdline, set in step 1):
```
vfio-pci.ids=8086:3e98
```

**Method B** (via modprobe.d):
```bash
echo "options vfio-pci ids=8086:3e98" > /etc/modprobe.d/vfio.conf
echo "blacklist i915" > /etc/modprobe.d/blacklist-igpu.conf
update-initramfs -u -k all
```

Method A is preferred for cleaner management. Method B is necessary when the device driver needs to be blacklisted (e.g., i915 for Intel iGPU).

### 4. Verify IOMMU Groups

```bash
# Check the device is in an isolated IOMMU group
find /sys/kernel/iommu_groups/ -type l | grep -i "0000:00:02"

# Verify driver binding
lspci -nnk -s 00:02.0 | grep "Kernel driver in use"
# Should show: vfio-pci
```

### 5. Configure the VM

```bash
# Add the PCI device as a passthrough device
qm set <VMID> -hostpci0 <PCI_ADDR>,pcie=1,x-vga=1

# Remove emulated VGA (so the passthrough GPU becomes primary)
qm set <VMID> -vga none
```

Key flags:
- `pcie=1` — treat as PCIe device (required for GPU passthrough)
- `x-vga=1` — mark as primary VGA device (for GPU/display passthrough)
- `rombar=0` — hide the option ROM (for NVMe/USB devices, may speed up boot)

VM requirements for GPU passthrough:
- `bios: ovmf` (UEFI, not SeaBIOS)
- `machine: q35` (PCIe topology support)
- The VM must be **stopped and started** (power cycle), not just rebooted, for hostpci changes to take effect

### 6. Boot and Verify

```bash
qm start <VMID>
```

Inside the VM:
```bash
lspci -nn | grep <VENDOR:DEVICE>
# Should show the device
lspci -nnk -s <PCI_ADDR> | grep "Kernel driver in use"
# Should show the native driver (e.g., i915 for Intel GPU)
```

For GPU passthrough with Wayland (GNOME):
```bash
# Check DRM devices
ls -la /dev/dri/

# Check display connectors
ls /sys/class/drm/

# Check connection status
cat /sys/class/drm/card0-HDMI-A-1/status
```

### 7. Configure USB Peripheral Passthrough

For keyboard, mouse, or other HID devices, pass through individual USB devices by vendor:product ID (stable across reboots — unlike bus-port addressing):

```bash
# Identify USB devices on the PVE host
lsusb

# Pass through by vendor:product ID
qm set <VMID> -usb<N> host=<VENDOR>:<PRODUCT>

# Example — wireless keyboard+mouse combo
qm set 111 -usb2 host=1a2c:2124   # SEM USB Keyboard
qm set 111 -usb3 host=1a86:e30a   # QinHeng composite (mouse)
```

**Inside the VM**, verify:
```bash
lsusb | grep -iE 'keyboard|mouse'
cat /proc/bus/input/devices | grep -E 'Mouse|Keyboard'
```

**Caveats:**
- Prefer `host=VENDOR:PRODUCT` over `host=bus-port` (bus-port numbers change on reboot)
- Passed-through USB devices connect through the VM's QEMU XHCI controller
- VM must be power-cycled for new USB devices to appear
- For composite devices (e.g., QinHeng with both keyboard+mouse interfaces), passing the single composite VID:PID exposes both HID interfaces

### 8. Configure Wayland Display Scaling for 4K TV

On a 4K display at typical TV-viewing distance, 100% scaling makes UI elements too small. For GNOME Wayland:

```bash
# Inside the VM, as the desktop user:
gsettings set org.gnome.mutter experimental-features "['scale-monitor-framebuffer']"
gsettings set org.gnome.desktop.interface text-scaling-factor 2.0
gsettings set org.gnome.desktop.interface scaling-factor 0
```

- `scale-monitor-framebuffer` enables per-monitor fractional scaling
- `text-scaling-factor 2.0` = 200% scaling (4K looks like 1080p-equivalent UI)
- Also configurable via GNOME Settings → Displays → Scale

These commands must run as the desktop user (`DISPLAY=:0`), not via `qm guest exec` which lacks a D-Bus session.

## Pitfalls & Mitigation

### ZFS root vs GRUB
**The biggest trap on modern PVE.** Proxmox with ZFS root reads boot parameters from `/etc/kernel/cmdline`, not `/etc/default/grub`. Modifying GRUB config has no effect. Always verify with `cat /proc/cmdline` after reboot. If your params aren't there, use `/etc/kernel/cmdline` + `proxmox-boot-tool refresh`.

### iGPU passthrough quirks
- **Only one GPU**: If you pass through the host's only GPU, the PVE host loses all local video output. WebUI and SSH still work, but there's no recovery console. Accept this tradeoff explicitly before proceeding.
- **i915 blacklist**: For Intel iGPU passthrough, the i915 driver MUST be blacklisted on the host via modprobe.d (Method B), or you must use `vfio-pci.ids` in the kernel cmdline (Method A). Without this, the host claims the GPU and passthrough fails.
- **iGPU reset bug**: After the VM stops, the iGPU may not reset cleanly, requiring a full host reboot to reuse it.
- **OpRegion**: Intel iGPU passthrough requires the OpRegion to be properly detected. The Proxmox/KVM log should show: `info: OpRegion detected on Intel display <id>`. If missing, the display won't work inside the VM.
- **HDMI audio unavailable on Coffee Lake**: Coffee Lake (CFL) UHD 630 does NOT expose a separate PCI audio function (`00:02.1`). The HDMI audio is embedded in the VGA function but VFIO cannot expose it to the guest. Inside the VM, `lspci -nn -s 01:00.1` shows an empty slot — no driver binds. Workarounds: USB audio adapter (recommended), HDMI audio extractor, Bluetooth audio, or passing through the host's cAVS controller for analog output. Do NOT waste time reloading `snd_hda_intel` or tweaking ALSA — the device simply isn't there in the guest.

### VM must be power-cycled
`qm set` changes for `hostpci0` only take effect on VM **stop + start**, not reboot. The new PCI device won't appear in `lspci` inside the guest until the VM is fully restarted from the host.

### Display detection
- If no monitor/TV is connected at boot, the GPU may not enable all outputs.
- The LG TV connected via HDMI may show up as DP-3 or another DP connector depending on the Intel GPU's internal wiring.
- To force output, connect the display before booting the VM.
- If the display is detected but shows "disconnected", ensure the input source on the TV matches the physical port.

## Verification Checklist

After reboot:
- [ ] `cat /proc/cmdline` contains `intel_iommu=on` and `iommu=pt`
- [ ] `lspci -nnk -s <PCI_ADDR> | grep "Kernel driver"` shows `vfio-pci` on the host
- [ ] VM `qm config <VMID>` shows `hostpci0: <PCI_ADDR>,pcie=1,x-vga=1`
- [ ] VM `qm config <VMID>` shows `vga: none`
- [ ] VM `qm config <VMID>` shows `bios: ovmf` and `machine: q35`
- [ ] Inside VM: `lspci -nn | grep <VENDOR:DEVICE>` shows the device
- [ ] Inside VM: `lspci -nnk -s <PCI_ADDR> | grep "Kernel driver"` shows the native driver (e.g., `i915`)
- [ ] Inside VM: `ls /sys/class/drm/` shows display connectors (HDMI-A, DP, etc.)
- [ ] Display cable connected, TV on correct input → desktop visible

## References

- `references/hp-mini-igpu.md` — Session-specific details for HP ProDesk 600 G5 Mini Intel UHD 630 iGPU passthrough to LG TV (ZF). Covers boot config, VM config, display detection, USB peripheral passthrough by VID:PID, Wayland 200% scaling, and the Coffee Lake HDMI audio limitation.
- `proxmox-pci-passthrough-notes.md` — Additional troubleshooting notes (if applicable).