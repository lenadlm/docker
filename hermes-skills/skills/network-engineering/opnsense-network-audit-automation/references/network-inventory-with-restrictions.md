# Network Inventory (When OPNsense APIs Blocked)

Consolidated from `network-inventory-with-restrictions` skill. Gathering network inventory when DHCP/ARP APIs are inaccessible.

## Approach Summary
- **Problem**: Direct API/file access blocked by OPNsense firewall
- **Methodology**: Iterative combination of ARP table + Nmap scanning + terminal tools

## Fallback Chain
1. **ARP table**: `arp -a` + DNS resolution (`getent hosts`)
2. **Nmap scanning**: `nmap -sn` for live hosts
3. **Terminal tools**: when API/SSH file access denied

## Key Learnings
- `/var/dhcpd/var/db/dhcpd.leases` requires SSH environment
- Prioritize Nmap/ARP when OPNsense API fails
- SSH connectivity over Tailscale may require `-o StrictHostKeyChecking=accept-new`
- For Tailscale SSH policy denying root, connect via **Local IP** instead

## Required Tools
- Terminal access to OPNsense (SSH/password-auth)
- Root credentials
- Basic command-line familiarity