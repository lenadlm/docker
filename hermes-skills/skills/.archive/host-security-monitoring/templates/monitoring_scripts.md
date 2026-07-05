# Daily Monitoring Templates

## Security Report Script (~/security_report.py)
Captures Fail2Ban (24h), CrowdSec decisions, and Auditd login failures.
```python
# [Insert version from session: includes Fail2Ban grep, cscli json, and ausearch]
```

## Docker Health Script (~/docker_report.py)
Captures container status, port mappings, resource usage (CPU/Mem), and `docker system df`.
```python
# [Insert version from session: includes docker info, ps, stats, and df parsing]
```

## Maintenance & Version Script (~/maintenance_report.py)
Compares `hermes --version` with GitHub API releases and lists daily `dpkg` updates.
```python
# [Insert version from session: includes GitHub API fetch and dpkg grep]
```
