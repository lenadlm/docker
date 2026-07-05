# Deploying Nmap on OPNsense for Network Discovery

Consolidated from `gateway-native-nmap-deployment` skill.

## Trigger
Use when you need a full network scan including MAC addresses and vendor identification, but only have SSH access to an OPNsense/FreeBSD gateway where `nmap` is not installed.

## Procedure

### 1. Verify
```bash
ssh <user>@<gateway_ip> "which nmap"
```

### 2. Install (FreeBSD pkg)
```bash
ssh <user>@<gateway_ip> "pkg install -y nmap"
```

### 3. Run host discovery scan
```bash
# Full subnet scan from gateway for Layer 2 visibility (MAC addresses)
ssh <user>@<gateway_ip> "nmap -sn 192.168.1.0/24"
```

### 4. Correlate with ARP table
```bash
ssh <user>@<gateway_ip> "arp -a"
```

## Pitfalls
- OPNsense does not include `nmap` in base install — must use `pkg`
- Use absolute path `/usr/local/bin/nmap` if path issues arise
- Root/sudo required for both install and raw socket scans
- Use `background=true` for large subnets to avoid terminal timeout