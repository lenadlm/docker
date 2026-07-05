# VLAN Discovery Example — OPNsense Dual Subnet

## Topology
- **OPNsense** (192.168.1.1) serves as gateway for both subnets
- **LAN**: 192.168.1.0/24 — interface enp6s18
- **VLAN**: 192.168.2.0/24 — routed through OPNsense

## Discovery Commands Used

### 1. Detect the VLAN subnet
```bash
# Check all local interfaces for non-primary subnets
ip addr show | grep "inet "

# Check routing table for additional RFC1918 routes
ip route show | grep -E "192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\."

# Verify router identity
curl -s -I http://192.168.1.1 | grep -i server
# Returns: Server: OPNsense
```

### 2. Ping sweep the VLAN (through router)
```bash
sudo nmap -sn 192.168.2.0/24
# Result (May 2026): 2 hosts up
#   192.168.2.1 — OPNsense VLAN interface
#   192.168.2.224 — DNS resolver
```

### 3. Port scan VLAN hosts
```bash
# Known gateways often have common ports
sudo nmap -sS -p 22,80,443,53,3000 -T4 --open 192.168.2.1
# Result: 22(SSH), 80(HTTP), 443(HTTPS), 3000(PPP)

# Unknown hosts — full TCP scan
sudo nmap -p- --min-rate=500 -T4 --open --host-timeout=30s 192.168.2.224
# Result: 53(DNS) only — dedicated DNS resolver
```

### 4. Combined scan command
```bash
# Ping both subnets in one call
sudo nmap -sn 192.168.1.0/24 192.168.2.0/24

# Port scan both subnets
sudo nmap -sS -p 22,80,443,53,111,135,139,445,2049,3000,\
3389,8080,8443,9090,10000,32400,7878,8096,9091 -T4 --open \
192.168.1.0/24 192.168.2.0/24
```

## Known VLAN Hosts
| Address | Identity | Services | Notes |
|---------|----------|----------|-------|
| 192.168.2.1 | OPNsense (VLAN IF) | 22/SSH, 80/HTTP, 443/HTTPS, 3000 | Same firewall, different interface |
| 192.168.2.224 | DNS Resolver | 53/DNS | No other open ports |

## Pitfalls
- VLAN isolation may block cross-subnet scanning entirely from LAN side
- Scanning through router: source MAC is router's, not target's — OS detection unreliable
- Use `-T4 --host-timeout=30s` to prevent hanging on unresponsive ranges
- Full TCP scan (-p-) on VLAN hosts can take 10-30s per host through the router