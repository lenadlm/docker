# Auditd File Integrity Rules

Deploy persistent file-watch rules to monitor critical system files for unauthorized changes.

## Rule Set (12 watches)

| Key | Path | Purpose |
|-----|------|---------|
| shadow_watch | `/etc/shadow` | Password hashes |
| passwd_watch | `/etc/passwd` | User accounts |
| group_watch | `/etc/group` | Group membership |
| gshadow_watch | `/etc/gshadow` | Group passwords |
| sshd_config | `/etc/ssh/sshd_config` | SSH daemon config |
| ssh_config | `/etc/ssh/ssh_config` | SSH client config |
| sudoers_watch | `/etc/sudoers` | Sudo permissions |
| sudoers_dir | `/etc/sudoers.d/` | Sudo drop-in files |
| pam_watch | `/etc/pam.d/` | PAM auth config |
| security_watch | `/etc/security/` | Security limits config |
| crontab_watch | `/etc/crontab` | System cron |
| crond_watch | `/etc/cron.d/` | Cron drop-in jobs |

## Deployment

```bash
# Write rules file (overwrites existing — the -D at top clears old rules)
sudo tee /etc/audit/rules.d/audit.rules > /dev/null << 'RULES'
## First rule - delete all
-D
## Buffer size
-b 8192
## Backlog wait time
--backlog_wait_time 60000
## Failure mode: syslog only (never use -f 2 = panic)
-f 1

## File watches (-p wa = write + attribute change)
-w /etc/shadow -p wa -k shadow_watch
-w /etc/passwd -p wa -k passwd_watch
-w /etc/group -p wa -k group_watch
-w /etc/gshadow -p wa -k gshadow_watch
-w /etc/ssh/sshd_config -p wa -k sshd_config
-w /etc/ssh/ssh_config -p wa -k ssh_config
-w /etc/sudoers -p wa -k sudoers_watch
-w /etc/sudoers.d/ -p wa -k sudoers_dir
-w /etc/pam.d/ -p wa -k pam_watch
-w /etc/security/ -p wa -k security_watch
-w /etc/crontab -p wa -k crontab_watch
-w /etc/cron.d/ -p wa -k crond_watch
RULES

# Load rules (persistent across reboots)
sudo augenrules --load

# Verify
sudo auditctl -l
```

## Usage

```bash
# Search for events by key
sudo ausearch -k sshd_config -ts today

# Authentication report
sudo aureport -au -ts today

# File access report
sudo aureport -f -i -ts today

# Follow live events
sudo tail -f /var/log/audit/audit.log | ausearch --interpret
```

## Notes

- **`-f 1` is critical:** Sets failure mode to syslog logging (not silent `-f 0` or panic `-f 2`). If auditd can't write rules, it logs the error and continues — the system stays running.
- **Persistence:** Rules in `/etc/audit/rules.d/audit.rules` are loaded by `auditd.service` on system start via `augenrules`. Rules added directly via `auditctl -w` are lost on reboot.
- **Log rotation:** Configured in `/etc/audit/auditd.conf` — default 100MB per file, 12 rotations, `max_log_file_action = ROTATE`. Sufficient for file-watch-level event volume.
- **Performance impact:** Negligible. File watches on 12 paths generate minimal events during normal operation. High event volume only occurs during active compromise or misconfigured software.
- **Daily security digest coverage:** The 08:00 EAT security digest queries `ausearch -m USER_LOGIN -ts today` for failed logins. The file-watch keys are searchable ad-hoc but not included in the automated digest (low signal-to-noise).