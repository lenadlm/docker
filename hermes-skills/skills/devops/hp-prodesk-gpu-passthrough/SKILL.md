---
name: hp-prodesk-gpu-passthrough
description: Single-GPU passthrough of Intel UHD 630 (Coffee Lake) on HP ProDesk 600 G5 Mini to a Proxmox VM. Includes known limitations (no HDMI audio, no secondary GPU), host kernel config, and rollback.
---

# HP ProDesk 600 G5 Mini — Intel UHD 630 GPU Passthrough

## Hardware Context

- **Machine**: HP ProDesk 600 G5 Desktop Mini
- **GPU**: Intel UHD 630 (Coffee Lake, PCI ID `8086:3e98`)
- **Outputs**: HDMI + DisplayPort on the machine
- **Limitation**: **No PCIe slot** — no second GPU possible. Single-GPU passthrough only
- **Host**: Proxmox VE (ZFS root), OVMF + q35 for passthrough VM

## Known Limitation: HDMI Audio

On Coffee Lake (and most Intel iGPUs before DG2/Alchemist), the HDMI audio codec is **embedded inside the VGA function** of the GPU — it is NOT exposed as a separate PCI function. Therefore:

- `lspci` on host shows only `00:02.0` (VGA), no `00:02.1` (audio)
- VFIO cannot separate audio from video
- Inside the guest, the GPU shows `01:00.0` (VGA) and possibly a phantom `01:00.1` (empty, no driver binds)
- **HDMI audio via GPU passthrough is not possible** on this hardware
- Workarounds: USB audio dongle, Bluetooth speaker, HDMI audio extractor

## Host Setup (Apply on Proxmox)

### 1. Kernel cmdline (`/etc/kernel/cmdline`)

Add IOMMU and vfio-pci binding:

```
intel_iommu=on iommu=pt vfio-pci.ids=8086:3e98
```

Keep existing params (ZFS root, zswap, etc.).

### 2. Apply bootloader

After editing `/etc/kernel/cmdline`:

```bash
proxmox-boot-tool refresh
```

### 3. Reboot

Reboot the Proxmox host for changes to take effect.

## VM Configuration (Proxmox)

### Enable passthrough:

```bash
qm set <VMID> --hostpci0 00:02.0,pcie=1,x-vga=1
qm set <VMID> --vga none
```

### USB device passthrough (individual devices to keep host USB controller accessible):

```bash
qm set <VMID> --usbN host=<vendor:product>
```

### Verify inside guest:

```bash
# GPU detected
lspci -nn | grep Intel
dmesg | grep i915

# Display connected
cat /sys/class/drm/card*-DP-*/status
cat /sys/class/drm/card*-DP-*/modes
```

## Admin Access During Passthrough

With `vga: none`, Proxmox VNC shows black — this is expected. Use:

1. **SSH** to the VM (`ssh user@<vm-ip>`)
2. **Serial console** via Proxmox: `qm set <VMID> --serial0 socket --vga serial0`, then `qm terminal <VMID>`

## Rollback (Restoring Normal VM)

1. Stop VM:
   ```bash
   qm stop <VMID>
   ```

2. Remove passthrough:
   ```bash
   qm set <VMID> --delete hostpci0
   qm set <VMID> --vga std
   qm set <VMID> --delete usb0   # repeat for usb1..N
   ```

3. Start VM — VNC restored.

4. (Optional) Remove host IOMMU/vfio config:
   - Edit `/etc/kernel/cmdline`, remove `intel_iommu=on iommu=pt vfio-pci.ids=8086:3e98`
   - `proxmox-boot-tool refresh`
   - Reboot Proxmox
   - Host iGPU returns to `i915` driver