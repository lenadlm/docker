#!/usr/bin/env bash
set -euo pipefail

# ──────────────────────────────────────────────────
# Hermes Agent — Skill Sync Script
# ──────────────────────────────────────────────────
# Mode: --push   (local → git, run on main Hermes)
#       --pull   (git → local, run on VPS Hermes)
#       --once   (git → ~/.hermes/skills/, no git pull)
# ──────────────────────────────────────────────────

SKILLS_REPO="$HOME/projects/hermes-skills"
HERMES_SKILLS="$HOME/.hermes/skills"
LOG="$SKILLS_REPO/sync.log"

log()  { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; echo "$*"; }
err()  { log "ERROR: $*"; exit 1; }

# Safety: ensure required dirs exist
[ -d "$SKILLS_REPO" ] || err "Skills repo not found at $SKILLS_REPO"
[ -d "$HERMES_SKILLS" ] || err "Hermes skills not found at $HERMES_SKILLS"

# ── Push: copy local skills → git, commit, push ──
push_skills() {
    log "Syncing skills: ~/.hermes/skills/ → git repo..."

    # Copy all skill files (SKILL.md, references/, scripts/, templates/)
    rsync -a --delete \
        --exclude='.env' \
        --exclude='*.secret*' \
        --exclude='*token*' \
        --exclude='*credential*' \
        --exclude='__pycache__' \
        --exclude='.git' \
        "$HERMES_SKILLS/" "$SKILLS_REPO/skills/"

    cd "$SKILLS_REPO"

    # Track removals too
    git add -A skills/ README.md .gitignore 2>/dev/null || true

    if git diff --cached --quiet; then
        log "No skill changes to commit."
        return 0
    fi

    COUNT=$(git diff --cached --stat -- skills/ | tail -1 | awk '{print $1}')
    git commit -m "sync skills: $(date '+%Y-%m-%d %H:%M') — $COUNT"
    git push origin main 2>&1 >> "$LOG" || log "Push failed (network? will retry next cycle)"
    log "Skills pushed successfully."
}

# ── Pull: git pull → copy skills → ~/.hermes/skills/ ──
pull_skills() {
    log "Syncing skills: git repo → ~/.hermes/skills/..."

    cd "$SKILLS_REPO"
    git pull origin main 2>&1 >> "$LOG" || log "Pull failed (network? will retry next cycle)"

    if [ ! -d "$SKILLS_REPO/skills" ]; then
        log "No skills directory in repo after pull."
        return 0
    fi

    # Copy new/changed skills into Hermes skills dir
    rsync -a \
        --exclude='.env' \
        --exclude='*.secret*' \
        --exclude='*token*' \
        --exclude='*credential*' \
        --exclude='__pycache__' \
        "$SKILLS_REPO/skills/" "$HERMES_SKILLS/"

    log "Skills pulled successfully."
}

# ── Once: copy from existing repo (no git pull) ──
once_skills() {
    log "One-time import: git repo → ~/.hermes/skills/..."

    if [ ! -d "$SKILLS_REPO/skills" ]; then
        log "No skills directory in repo."
        return 0
    fi

    rsync -a \
        --exclude='.env' \
        --exclude='*.secret*' \
        --exclude='*token*' \
        --exclude='*credential*' \
        --exclude='__pycache__' \
        "$SKILLS_REPO/skills/" "$HERMES_SKILLS/"

    log "One-time import complete."
}

# ── Main ──
case "${1:-}" in
    --push) push_skills ;;
    --pull) pull_skills ;;
    --once) once_skills ;;
    *)
        echo "Usage: $0 --push | --pull | --once"
        echo "  --push   Local → git (run on main Hermes)"
        echo "  --pull   Git → local (run on VPS, does git pull)"
        echo "  --once   Git → local (skip git pull, for first run)"
        exit 1
        ;;
esac