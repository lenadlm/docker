# Host Maintenance and Reporting

## Hermes Version Check
To compare local vs latest version in a report:
1. Current: `hermes --version`
2. Latest: `curl -s https://api.github.com/repos/NousResearch/hermes-agent/releases/latest | jq -r .tag_name`
3. Changelog: Extract from `.body` of the releases API.

## System Updates Audit
To summarize package changes since last run:
`grep ' status installed ' /var/log/dpkg.log | grep $(date +%Y-%m-%d)`

## Tailscale Connectivity Probes
When `accept-routes` is on, verify subnet reachability:
`ping -c 2 -W 2 <gateway_ip_of_subnet>`
Check for IP conflicts with Docker:
`ip addr | grep -E "tailscale|docker|br-"`
