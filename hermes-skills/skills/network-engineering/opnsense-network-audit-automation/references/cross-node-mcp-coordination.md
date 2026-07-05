# Cross-Node MCP Coordination

Consolidated from `cross-node-mcp-coordination` skill. Manager-Worker coordination between Hermes Agent instances across a network (Tailscale or Local).

## Two Approaches

### Direct MCP Bridge (Preferred)
1. On worker node: `hermes mcp serve --port <PORT> --host 0.0.0.0`
2. On manager node: add to `config.yaml` under `mcp_servers`
3. Verify: `curl -s http://<IP>:<PORT>/health`

### Delegation Fallback (Robust)
If port binding or firewall issues prevent MCP exposure:
```python
delegate_task(
    goal="Run command on worker node",
    context="SSH access: ssh -i <KEY> <USER>@<IP>",
    toolsets=['terminal']
)
```

## Pitfalls
- **Port conflict**: Common ports (8080, 8888) often occupied — check `netstat -tuln` first
- **Binding**: Explicitly bind to Tailscale IP or `0.0.0.0`, not localhost
- **Tailscale SSH policy**: Even with OS-level SSH, Tailscale's own ACLs may block
- **SSH key management**: Standardize key location across all managed nodes