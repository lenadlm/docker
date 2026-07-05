# SSH Infrastructure Access Verification

Consolidated from `ssh-infrastructure-access-verification` skill. Diagnostic workflow for verifying SSH access to infrastructure across multiple paths.

## Multi-Path Probing Strategy
When connecting to remote infrastructure (e.g., `srv` node):

1. If Tailscale IP fails ("Policy Denied"), try **Public IP** to verify SSH daemon is functional
2. If both fail, check firewall rules and Tailscale ACLs

## Key Practices

### Automated Trust
```bash
ssh -o StrictHostKeyChecking=accept-new user@ip "hostname"
```
Allows agent to trust new hosts without interactive prompts while still blocking changes to existing host keys.

### Host Key Reset
```bash
# Clear stale keys
ssh-keygen -R <ip>
# Or reset entirely (automated environments only)
rm -f ~/.ssh/known_hosts
```

### Key Generation for Specific Nodes
```bash
ssh-keygen -t rsa -b 4096 -f ~/.hermes/id_rsa_node -N ""
```

## Distinguishing Connection Failures
- **"Connection Refused"**: Service down or firewall blocking (service-level issue)
- **"Tailnet policy does not permit"**: Tailscale ACL restricting SSH (central policy issue)
- **"Host key verification failed"**: Key mismatch since last connection (stale known_hosts)

## Pitfalls
- Even if `tailscale set --ssh` is run, central Tailnet policy may still block
- Some nodes bind SSH server to specific interfaces only (127.0.0.1 or Tailscale IP)
- Standardize key location (e.g., `~/.hermes/srv_id_rsa`) to keep management keys separate from personal keys