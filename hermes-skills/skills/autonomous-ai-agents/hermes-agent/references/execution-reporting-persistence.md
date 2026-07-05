# Hermes Process Reporting Implementation Details (May 2026)

## Implementation Summary
A persistent execution reporting system for Hermes designed to survive reboots, updates, and crashes.

### Key Components
1. **HermesConfig**: Centralized config loading with internal defaults, `config.yaml` merging, and environment variable overrides.
2. **HermesProcessManager**: Core class for per-process Markdown reports and JSON state persistence.
3. **Boot Recovery**: Logic to detect `RUNNING` or `INTERRUPTED` statuses from dead PIDs and transition them to `PENDING_RESUME`.

### Configuration (config.yaml)
```yaml
process_reporting:
  enabled: true
  retention_count: 10
  atomic_writes: true
  state_dir: "~/.hermes/process_state"
  logs_dir: "~/.hermes/process_logs"

recovery:
  auto_resume: true
  max_retries: 3
```

### Environment Overrides
- `HERMES_REPORTING_ENABLED`
- `HERMES_REPORTING_RETENTION`
- `HERMES_AUTO_RESUME`

### Directory Layout
- `~/.hermes/process_logs/`: Markdown execution reports (`process_<PID>_<agent>.md`).
- `~/.hermes/process_state/`: Structured JSON state for recovery.
- `~/.hermes/logs/`: Raw tool/system logs.

### Recovery Rules
- If a process is dead but state is `RUNNING`, mark `PENDING_RESUME`.
- Use `instruction_hash` and `session_id` to prevent duplicate or conflicting resumes.
- Append "Recovery Information" section to Markdown on resume.
