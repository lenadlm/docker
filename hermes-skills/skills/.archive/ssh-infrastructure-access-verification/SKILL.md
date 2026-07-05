---
name: ssh-infrastructure-access-verification
description: Diagnostic workflow for verifying SSH access to infrastructure across multiple paths (Public IP, Tailscale, Local) with automated key management.
---

# SSH Infrastructure Access Verification

## Approach Summary
When connecting to remote infrastructure (like an `srv` node), connectivity often fails due to firewall rules, Tailscale ACLs, or host key mismatches. This skill provides a systematic pivot strategy.

## Methodology
1. **Multi-Path Probing**: If Tailscale IP fails with "Policy Denied", attempt connection via Public IP to verify the SSH daemon and credentials are functional.
2. **Automated Trust**: Use `-o StrictHostKeyChecking=accept-new` in autonomous scripts to allow the agent to trust new hosts without interactive prompts, while still blocking changes to existing host keys.
3. **Reset Flow**: If "Host key verification failed" occurs, use `rm -f ~/.ssh/known_hosts` (or `ssh-keygen -R <ip>`) to clear stale keys before regenerating/retesting.
4. **Tailscale Debugging**: Differentiate "Connection Refused" (Service down/Firewall) from "Tailnet policy does not permit" (ACL restriction).

## Reusable Commands
```bash
# Automated key generation for specific node
ssh-keygen -t rsa -b 4096 -f ~/.hermes/id_rsa_node -N ""

# Test with automatic host trust
ssh -i ~/.hermes/id_rsa_node -o StrictHostKeyChecking=accept-new user@ip "hostname"
```

## Pitfalls
- **Tailscale ACLs**: Even if `tailscale set --ssh` is run on a node, the central Tailnet policy may still block the connection.
- **Port 22 vs UI**: Some nodes may have SSH server active but restricted to specific interfaces (127.0.0.1 or Tailscale IP only).
