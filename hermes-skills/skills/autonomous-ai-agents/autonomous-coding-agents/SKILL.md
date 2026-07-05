---
name: autonomous-coding-agents
description: "Delegate coding tasks to autonomous coding agent CLIs (Claude Code, Codex, OpenCode) — orchestrate from Hermes terminal/process tools for features, PRs, refactoring, and batch issue fixing."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Coding-Agent, Claude-Code, Codex, OpenCode, Autonomous, Refactoring, Code-Review, Automation, Orchestration]
    related_skills: [github-pr-workflow, github-code-review]
---

# Autonomous Coding Agents

Orchestrate external coding agent CLIs from Hermes. Each agent provides a different AI backend for autonomous coding — use the right one for the task.

## When to Use

- User asks to use any of: Claude Code, Codex, OpenCode
- You want an external agent to autonomously implement, refactor, or review code
- Long-running coding tasks where Hermes monitors progress
- Parallel workflows across multiple worktrees/issues

## Common Patterns (all agents)

All three agents share these patterns:

### One-shot tasks
```bash
# Claude Code (preferred - cleanest print mode)
claude -p "Add error handling to API calls" --allowedTools "Read,Edit" --max-turns 10

# Codex
codex exec "Add error handling to API calls"

# OpenCode
opencode run "Add error handling to API calls"
```

### Long-running background tasks
```bash
# Start in background
terminal(command="...command...", background=true, pty=true)
# Monitor
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")
# Send input if agent asks a question
process(action="submit", session_id="<id>", data="yes")
```

### PR review
Clone to temp directory for isolation:
```bash
REVIEW=$(mktemp -d)
git clone https://github.com/user/repo.git $REVIEW
cd $REVIEW
# Then run agent-specific review command
```

### Parallel work with git worktrees
```bash
# Create isolated worktree
git worktree add -b fix/issue-78 /tmp/issue-78 main
# Launch agent in worktree
terminal(command="agent-command", workdir="/tmp/issue-78", background=true, pty=true)
# Cleanup
git worktree remove /tmp/issue-78
```

## Agent Selection Guide

| Task | Best Agent | Reason |
|------|-----------|--------|
| Quick one-shot fix | Claude Code (-p mode) | Cleanest non-interactive, structured JSON output |
| Multi-turn iteration | OpenCode or Claude Code (tmux) | Best interactive TUI |
| Sandboxed execution | Codex | Built-in sandbox, --full-auto for safe automation |
| Budget-limited task | Claude Code | --max-budget-usd flag |
| Cost tracking | OpenCode | Built-in `opencode stats` command |
| Provider-agnostic | OpenCode | Works with OpenRouter, any API provider |
| CI/CD automation | Claude Code --bare | Fastest startup, no hooks/plugins |

## Pitfalls (all agents)

1. **Most agents need a git repo** — Codex refuses to run outside one. Use `mktemp -d && git init` for scratch work.
2. **PTY required for interactive TUI** — Claude Code interactive, Codex, and OpenCode TUI all need `pty=true`. Claude Code `-p` mode and OpenCode `run` mode do NOT need pty.
3. **Don't share working directories** across parallel agent sessions — use worktrees or separate temp dirs.
4. **Set explicit limits** — use `--max-turns` (Claude), budget limits, or narrow file scoping to prevent runaway loops.
5. **Check git status after agent completes** — review `git diff` and run tests before committing blindly.
6. **Background tmux sessions persist** — always clean up with `tmux kill-session -t <name>` when done.

---

## Claude Code (Anthropic)

Delegate coding tasks to [Claude Code](https://code.claude.com/docs/en/cli-reference) — Anthropic's autonomous coding agent CLI.

### Prerequisites
```bash
npm install -g @anthropic-ai/claude-code
claude auth login          # OAuth (Pro/Max) or
claude auth login --console  # API key billing
claude --version           # Requires v2.x+
```

### Mode 1: Print Mode (`-p`) — NON-INTERACTIVE (PREFERRED)

```bash
terminal(command="claude -p 'Add error handling to all API calls in src/' --allowedTools 'Read,Edit' --max-turns 10", workdir="/path/to/project", timeout=120)
```

Print mode skips ALL dialogs — no workspace trust, no permissions confirmations. Ideal for automation.

**Structured JSON output:**
```bash
claude -p 'Analyze auth.py for security issues' --output-format json --max-turns 5
```

**Piped input:**
```bash
cat src/auth.py | claude -p 'Review this code for bugs' --max-turns 1
```

### Mode 2: Interactive via tmux — MULTI-TURN

```bash
# Start tmux session
terminal(command="tmux new-session -d -s claude-work -x 140 -y 40")
terminal(command="tmux send-keys -t claude-work 'cd /path/to/project && claude' Enter")
# Handle trust dialog
terminal(command="sleep 4 && tmux send-keys -t claude-work Enter")
# Send task
terminal(command="tmux send-keys -t claude-work 'Refactor the auth module' Enter")
# Monitor progress
terminal(command="sleep 15 && tmux capture-pane -t claude-work -p -S -50")
```

### Key Flags
| Flag | Effect |
|------|--------|
| `-p, --print` | Non-interactive one-shot mode |
| `--max-turns <n>` | Cap agentic loops (print mode) |
| `--max-budget-usd <n>` | Cap API spend |
| `--model <alias>` | `sonnet`, `opus`, `haiku` |
| `--output-format json` | Structured JSON result |
| `--dangerously-skip-permissions` | Auto-approve ALL tool use |
| `--bare` | Skip OAuth/plugins/MCP (needs API key) |
| `--allowedTools <tools>` | Whitelist: `Read,Edit,Write,Bash` |

**Session continuation:**
```bash
# Resume most recent
claude -p 'Continue with next step' --continue
# Resume specific session
claude -p 'Continue work' --resume <session-id>
```

### Cost & Performance
- Use `--max-turns 5-10` for most tasks
- Use `--effort low` for simple tasks, `high` for complex
- Use `--model haiku` for cheap/simple, `opus` for complex
- Monitor with `/context` in interactive mode (compact at >70%)

---

## Codex (OpenAI)

Delegate coding tasks to [Codex](https://github.com/openai/codex) — OpenAI's autonomous coding agent CLI.

### Prerequisites
```bash
npm install -g @openai/codex
`OPENAI_API_KEY` or Codex OAuth credentials
```

### One-shot tasks
```bash
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

### Key Flags
| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution |
| `--full-auto` | Sandboxed, auto-approves file changes |
| `--yolo` | No sandbox, no approvals (fastest) |
| `--sandbox danger-full-access` | Bypass sandbox for gateway contexts |

### Hermes Gateway Caveat
Codex sandboxing may fail in gateway/service contexts with bubblewrap errors. Prefer:
```bash
codex exec --sandbox danger-full-access "<task>"
```

### PR reviews
```bash
REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW
cd $REVIEW && gh pr checkout 42
codex review --base origin/main
```

### Rules
1. Always use `pty=true` — interactive terminal app
2. Git repo required — use `mktemp -d && git init` for scratch
3. Use `exec` for one-shots — runs and exits cleanly
4. Background for long tasks with `process` monitoring

---

## OpenCode

Use [OpenCode](https://opencode.ai) — a provider-agnostic, open-source AI coding agent.

### Prerequisites
```bash
npm i -g opencode-ai@latest
opencode auth login
# Verify: opencode auth list
```

### One-shot tasks
```bash
terminal(command="opencode run 'Add retry logic to API calls and update tests'", workdir="~/project")
```
Attach context files:
```bash
opencode run 'Review this config for security issues' -f config.yaml -f .env.example
```

### Interactive TUI (Background)
```bash
terminal(command="opencode", workdir="~/project", background=true, pty=true)
process(action="submit", session_id="<id>", data="Implement OAuth refresh flow")
# Monitor
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")
# Exit with Ctrl+C
process(action="write", session_id="<id>", data="\x03")
# or
process(action="kill", session_id="<id>")
```

### Key Flags
| Flag | Effect |
|------|--------|
| `run 'prompt'` | One-shot execution (no pty needed) |
| `-c, --continue` | Continue last session |
| `-s <id>` | Continue specific session |
| `--model provider/model` | Force specific model |
| `--file <path>` / `-f` | Attach file(s) |
| `--thinking` | Show model thinking |

### Cost tracking
```bash
opencode stats
opencode stats --days 7 --models anthropic/claude-sonnet-4
```

### Pitfalls
- `/exit` is NOT a valid command — use Ctrl+C or `process(action="kill")`
- PATH can resolve wrong binary — check with `which -a opencode`
- Interactive TUI requires `pty=true`; `opencode run` does NOT