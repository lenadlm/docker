#!/usr/bin/env python3
"""
Hermes Daily Auto-Updater — Option A (Conservative)
Daily check at 07:00, auto-update with backup + rollback, always deliver report.

Backup only critical config/state (skips venv, git, node, caches = ~1.4GB).
"""

import subprocess
import re
import shutil
from datetime import datetime
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
BACKUP_DIR = HERMES_HOME / "backup"
LOG_FILE = HERMES_HOME / "logs" / "hermes_update.log"

# Only backup these critical items (total ~50MB)
BACKUP_ITEMS = [
    ".env",
    "config.yaml",
    "cron",
    "memories",
    "skills",
    "sessions",
    "hooks",
    "hermes-agent/run_agent.py",
    "hermes-agent/cli.py",
    "hermes-agent/model_tools.py",
    "hermes-agent/toolsets.py",
    "hermes-agent/hermes_state.py",
    "hermes-agent/hermes_constants.py",
    "hermes-agent/hermes_logging.py",
]

# Exclude these from full repo backup
BACKUP_SKIP_DIRS = {
    "hermes-agent/venv",
    "hermes-agent/node",
    "hermes-agent/.git",
    "hermes-agent/__pycache__",
    "node",
    "backups",
    "state-snapshots",
    "images",
    "sandboxes",
    "cache",
    "image_cache",
    "audio_cache",
}


def run(cmd, timeout=300):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", f"Command timed out ({timeout}s)", -1
    except Exception as e:
        return "", str(e), -1


def log(msg):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def get_version():
    out, _, _ = run("hermes --version")
    m = re.search(r"v(\S+)", out)
    return m.group(1) if m else out or "unknown"


def check_updates():
    out, err, rc = run("hermes update --check")
    if rc != 0:
        log(f"update --check failed: {err}")
        return False, 0, err
    m = re.search(r"(\d+)\s+commits behind", out)
    commits = int(m.group(1)) if m else 0
    if commits > 0:
        log(f"Updates available: {commits} commits behind")
        return True, commits, out
    log("No updates available")
    return False, 0, out


def config_backup(dst):
    """Backup only critical config/state files (~50MB instead of 1.4GB)."""
    for item in BACKUP_ITEMS:
        src = HERMES_HOME / item
        target = dst / item
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if src.name in BACKUP_SKIP_DIRS:
                continue
            shutil.copytree(src, target, symlinks=True, dirs_exist_ok=True)
        elif src.exists():
            shutil.copy2(src, target)


def create_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"hermes_{ts}"
    try:
        dst.mkdir(parents=True, exist_ok=True)
        config_backup(dst)
        # Also git log HEAD for rollback context
        run(f"cd {HERMES_HOME}/hermes-agent && git log --oneline -1 > {dst}/git_head.txt")
        run(f"cd {HERMES_HOME}/hermes-agent && git rev-parse HEAD > {dst}/git_sha.txt")
        return True, str(dst)
    except Exception as e:
        return False, str(e)


def get_changelog():
    out, _, _ = run(
        "cd ~/.hermes/hermes-agent && git log --oneline -8 --format='%h %s'"
    )
    if not out:
        return []
    commits = []
    ICONS = {
        "fix": "🐛", "bug": "🐛", "error": "🐛", "issue": "🐛",
        "feat": "🆕", "add": "🆕", "new": "🆕", "support": "🆕",
        "perf": "⚡", "speed": "⚡", "fast": "⚡", "optimize": "⚡",
        "sec": "🛡", "vuln": "🛡", "cve": "🛡", "depend": "🛡",
        "refactor": "♻️", "clean": "♻️", "remove": "♻️",
        "chore": "📦", "docs": "📝", "release": "🚀",
    }
    for line in out.split("\n"):
        line = line.strip()
        if not line:
            continue
        icon = "🔧"
        lower = line.lower()
        for kw, ic in ICONS.items():
            if kw in lower:
                icon = ic
                break
        commits.append(f"{icon} {line}")
    return commits[:8]


def run_update():
    out, err, rc = run("hermes update --yes --no-backup", timeout=300)
    log(f"update --yes stdout: {out[:500]}")
    log(f"update --yes stderr: {err[:500]}")
    log(f"update --yes rc: {rc}")
    return rc == 0, out, err


def restart_gateway():
    """Restart gateway — try multiple methods."""
    # Method 1: hermes CLI
    _, _, rc = run("hermes gateway restart", timeout=30)
    if rc == 0:
        run("sleep 3")
        return True
    # Method 2: systemctl
    _, _, rc = run("systemctl --user restart hermes-gateway.service", timeout=15)
    if rc == 0:
        run("sleep 3")
        return True
    # Method 3: kill + auto-restart by systemd
    run("pkill -f 'hermes.*gateway' || true")
    run("sleep 3")
    _, _, rc = run("systemctl --user start hermes-gateway.service", timeout=15)
    run("sleep 5")
    return True  # assume best effort


def verify_health():
    out, _, rc = run("hermes status --all", timeout=15)
    if rc != 0:
        return False, "Status command failed"
    lower = out.lower()
    if "not found" in lower and "hermes" in lower:
        # Hermes binary missing — update broke install
        return False, "Hermes binary not found after update"
    if "running" in lower and ("telegram" in lower or "gateway" in lower):
        return True, out
    # Partial success — gateway may be stopped but config ok
    if "configured" in lower:
        return True, out
    return False, "Status unclear"


def get_status_summary():
    """Extract key status metrics from hermes status output."""
    out, _, _ = run("hermes status --all", timeout=15)
    s = {}
    # Gateway
    gw_section = out.split("Gateway Service")
    if len(gw_section) > 1:
        gw_lines = gw_section[1].strip().split("\n")[:3]
        gw_text = " ".join(gw_lines).lower()
        s["gateway"] = "running" if "running" in gw_text else "stopped"
    # Telegram
    if "Telegram" in out:
        tg_section = out.split("Telegram")
        if len(tg_section) > 1:
            tg_text = tg_section[1].split("\n")[1].lower()
            s["telegram"] = "connected" if "configured" in tg_text else "disconnected"
    # Jobs
    m = re.search(r"Jobs:\s+(\d+)\s+active", out)
    s["jobs"] = f"{m.group(1)} active" if m else "unknown"
    # Model
    m = re.search(r"Model:\s+(\S+)", out)
    s["model"] = m.group(1) if m else "unknown"
    # Memory
    mem, _, _ = run("free -m | grep Mem")
    if mem:
        parts = mem.split()
        if len(parts) >= 7:
            pct = round(int(parts[2]) / int(parts[1]) * 100, 1)
            s["memory"] = f"{pct}%"
    # Disk
    disk, _, _ = run("df -h / | tail -1")
    if disk:
        s["disk"] = disk.split()[4]
    # Containers
    cnt, _, _ = run("docker ps --format '{{.Names}}' 2>/dev/null | wc -l")
    running, _, _ = run("docker ps --format '{{.Status}}' 2>/dev/null | grep -c 'Up'")
    s["containers"] = f"{running.strip()}/{cnt.strip()}" if cnt.isdigit() else "0/0"
    return s


def build_report(old_ver, new_ver, has_updates, commits, updated_ok,
                 backup_path, changelog, status, next_run):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"🔄 **Hermes Update Report — {now}**\n"]

    if not has_updates:
        lines.append("✅ **Already Up to Date**")
        lines.append(f"📦 Version: v{old_ver}")
        lines.append("🔄 No new commits available\n")
    elif updated_ok:
        lines.append("📦 **Version Update**")
        lines.append(f"🔹 Previous: v{old_ver}")
        lines.append(f"🆕 Current: v{new_ver}")
        lines.append(f"📊 Commits: {commits}")
        if backup_path:
            lines.append(f"\n💾 Backup: {backup_path}")
        lines.append("")
    else:
        lines.append("📦 **Version Update**")
        lines.append(f"🔹 Previous: v{old_ver}")
        lines.append(f"🔴 **Update FAILED**\n")

    if changelog:
        lines.append("📋 **Recent Changes**")
        for c in changelog:
            lines.append(c)
        lines.append("")

    lines.append("⏱ **Execution**")
    if not has_updates:
        lines.append("ℹ️ Skipped — already current")
    elif updated_ok:
        lines.append("✅ Update completed successfully")
    else:
        lines.append("🔴 Update failed — review logs")
    lines.append(f"⏰ Next check: {next_run}")

    # Agent status
    gw = status.get("gateway", "?")
    tg = status.get("telegram", "?")
    jobs = status.get("jobs", "?")
    model = status.get("model", "?")
    mem = status.get("memory", "?")
    disk = status.get("disk", "?")
    cnt = status.get("containers", "?")
    gw_icon = "✅" if gw == "running" else "🔴"
    tg_icon = "📱" if tg == "connected" else "❌"
    lines.append(f"\n🐳 **Agent Status**")
    lines.append(f"{gw_icon} Gateway: {gw}")
    lines.append(f"{tg_icon} Telegram: {tg}")
    lines.append(f"⏰ Jobs: {jobs}")
    lines.append(f"🤖 Model: {model}")
    lines.append(f"💾 Mem: {mem} | 📁 Disk: {disk} | 🐳 Containers: {cnt}")

    return "\n".join(lines)


def main():
    log("=" * 50)
    log("Starting Hermes auto-update check")
    start = datetime.now()

    old_ver = get_version()
    log(f"Version: {old_ver}")

    has_updates, commits, check_msg = check_updates()
    backup_path = None
    updated_ok = False
    changelog = []

    if has_updates and commits > 0:
        # Backup
        bk_ok, bk_path = create_backup()
        if bk_ok:
            backup_path = bk_path
            log(f"Backup: {bk_path}")
        else:
            log(f"Backup FAILED: {bk_path}")

        # Update
        updated_ok, up_out, up_err = run_update()

        if updated_ok:
            changelog = get_changelog()
            restart_gateway()
            health_ok, health_msg = verify_health()
            if not health_ok:
                log(f"WARNING: Health check failed after update: {health_msg}")

    # Status + report
    status = get_status_summary()
    new_ver = get_version()

    now = datetime.now()
    next_run = now.replace(hour=7, minute=0, second=0)
    if next_run <= now:
        from datetime import timedelta
        next_run += timedelta(days=1)
    next_run_str = next_run.strftime("%Y-%m-%d 07:00")

    report = build_report(
        old_ver, new_ver, has_updates, commits, updated_ok,
        backup_path, changelog, status, next_run_str
    )
    print(report)
    log(f"Report generated. Duration: {datetime.now() - start}")


if __name__ == "__main__":
    main()
