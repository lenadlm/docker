# Branching Strategy

## Main Branches

| Branch | Purpose |
|---|---|
| `main` | **Stable, production-ready.** All commits must be reviewed and tested. |
| `experiments/` | **AI agent sandbox & experiments.** Branch off `main`, try things, merge or discard. |

## Experiment Branches

Use `experiments/<name>` for AI agent work, prototypes, and throwaway exploration:

```bash
# Create an experiment branch off main
git checkout -b experiments/n8n-webhook-tests main

# Work freely — no rules, no reviews
# ...

# If it works: merge back
git checkout main
git merge experiments/n8n-webhook-tests

# If it doesn't: discard
git branch -D experiments/n8n-webhook-tests
```

The `experiments/` prefix keeps them grouped and easy to clean up:

```bash
# List all experiment branches
git branch --list 'experiments/*'

# Clean up merged experiments
git branch -d $(git branch --list 'experiments/*' --merged main)

# Purge all stale experiments
git branch -D $(git branch --list 'experiments/*' --no-merged main)
```

## Convention

| Prefix | Use Case |
|---|---|
| `experiments/` | AI agent sandbox, throwaway prototypes |
| `fix/` | Bug fixes (e.g., `fix/portainer-ip-bug`) |
| `feature/` | New features (e.g., `feature/unifi-monitoring`) |

## Git Config

This repo uses **GPG-signed commits** (key `E6AF41D353CAD8E1`). To sign automatically:

```bash
git config user.signingkey E6AF41D353CAD8E1
git config commit.gpgsign true
```