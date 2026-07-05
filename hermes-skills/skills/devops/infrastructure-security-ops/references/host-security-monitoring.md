# Host Security Monitoring

Consolidated from `host-security-monitoring` skill. Covers Fail2Ban, CrowdSec, Auditd procedures.

## Core Security Services

### Fail2Ban
- **Logs**: `/var/log/fail2ban.log`
- **Logic**: Track `Ban` and `Unban` events
- **Status check**: `fail2ban-client status <jail>`

### CrowdSec
- **Tool**: `cscli decisions list -o json` for active bans
- Uses Local API (LAPI); ensure service is running

### Auditd (Linux Auditing System)
- **Logs**: `/var/log/audit/audit.log`
- **Search**: `ausearch` for structured queries (needs root)
- Failed logins: `ausearch -m USER_LOGIN,USER_AUTH -ts today --success no`
- Sensitive file modification: `ausearch -m SYS_CALL -k sensitive_files`

## Diagnostic: Inaccessible Port (e.g. 8888)

1. **Process binding**: `ss -tulpn | grep <port>`
2. **Local loopback**: `curl -v http://127.0.0.1:<port>/health`
3. **Interface IP test**: `curl -v http://<Tailscale-IP>:<port>/health`
4. **Interface audit**: `ip addr show tailscale0`
5. **Firewall order audit**: `sudo ufw status numbered` (deny rules can shadow allow rules)
6. **Tailscale fabric**: `tailscale status` / `tailping ping <peer-name>`

## Pitfalls
- **UFW rule shadowing**: A `deny` rule added later may not override earlier `allow` depending on position
- **Package conflicts**: `apt upgrade` can hang on config file prompts; check `ps aux | grep dpkg`
- **AppArmor denials**: Check `ausearch -m avc -ts today` if services fail to initialize
- **Telegram formatting**: No pipe tables — use bullets and labeled key-value pairs