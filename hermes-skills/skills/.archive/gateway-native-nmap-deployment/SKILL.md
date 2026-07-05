---
name: gateway-native-nmap-deployment
description: Steps for installing and using nmap directly on OPNsense/FreeBSD when standard API access is restricted.
---

# Deploying Nmap on OPNsense for Network Discovery

## Trigger Condition
Use this skill when you need a full network scan (including MAC addresses and vendor identification) but only have SSH access to an OPNsense/FreeBSD gateway where `nmap` is not yet installed.

## Procedure

### 1. Verification
Check if nmap is installed on the gateway:
```bash
ssh <user>@<gateway_ip> "which nmap"
```

### 2. Installation (OPNsense/FreeBSD)
Since OPNsense is based on FreeBSD, use `pkg` for installation. This requires an active internet connection on the gateway:
```bash
ssh <user>@<gateway_ip> "pkg install -y nmap"
```

### 3. Execution
Run a host discovery scan (ping scan) to map the local subnet. Running from the gateway ensures Layer 2 visibility (MAC addresses) which is often masked when scanning across subnets:
```bash
ssh <user>@<gateway_ip> "nmap -sn 192.168.1.0/24"
```

### 4. Inventory Correlation
Correlate `nmap` output with the system ARP table for the most accurate hostname-to-IP-to-MAC mapping:
```bash
ssh <user>@<gateway_ip> "arp -a"
```

## Pitfalls & Lessons Learned
- **Missing nmap:** OPNsense does not include `nmap` in the base install; it must be added via `pkg`.
- **Pathing:** If `which nmap` returns a path but the command fails, use the absolute path (usually `/usr/local/bin/nmap`).
- **Permissions:** Root or sudo access is required for both `pkg install` and `nmap` (especially for OS fingerprinting or raw socket scans).
- **Backgrounding:** For large subnets, use `background: true` to avoid terminal timeouts during the scan.

## Verification
Table results should include:
- Hostname (from DNS/Reverse Lookups)
- IP Address
- MAC Address
- MAC Vendor (provided by nmap's internal database)
