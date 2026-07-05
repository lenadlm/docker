---
name: cross-node-mcp-coordination
description: Multi-agent coordination and tool-sharing between remote Hermes instances using MCP and delegation fallbacks.
---

# Cross-Node MCP Coordination

## Approach Summary
Establishing a "Manager-Worker" relationship between two independent Hermes Agent instances across a network (Tailscale or Local).

## Methodology
1. **Direct MCP Bridge (Preferred):**
   - Expose the worker node's tools using `hermes mcp serve --port <PORT> --host 0.0.0.0`.
   - Add the remote endpoint to the manager's `config.yaml` under `mcp_servers`.
2. **Delegation Fallback (Robust):**
   - If port binding or firewall issues prevent direct MCP exposure, use `delegate_task`.
   - The manager agent spawns a worker subagent with a `terminal` toolset configured for SSH access to the target node.
   - This provides "virtual tool access" even when raw socket binding is blocked.

## Lessons Learned & Pitfalls
- **Port Conflict:** Common ports like `8080` are often occupied by existing dashboard services (e.g., Dozzle, Traefik). Always check `netstat -tuln` before selection.
- **Binding:** When running `mcp serve` over Tailscale, explicitly bind to the Tailscale IP or `0.0.0.0`; default `localhost` binding will be unreachable from the manager.
- **Tailscale SSH Policy:** Even if OS-level SSH is configured, Tailscale's own ACLs (`tailscale set --ssh`) and Tailnet policies may block the connection. Verification requires testing both Public and Tailnet IPs.
- **SSH Key Management:** Standardize key location (e.g., `~/.hermes/srv_id_rsa`) to keep management-specific keys separate from personal keys.

## Verification Steps
- Check worker connectivity: `curl -s http://<IP>:<PORT>/health`.
- Test delegation: `ssh -i <KEY> <USER>@<IP> "hostname"`.

## Related Skills
- `network-inventory-with-restrictions`
- `ssh-infrastructure-access-verification`
- `hermes-agent`
