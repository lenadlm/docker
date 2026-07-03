# ADR-001: Homelab Monorepo Structure

**Status:** Accepted  
**Date:** 2026-07-03  
**Deciders:** Leo (user), Hermes (agent)

## Context

All infrastructure configuration, automation scripts, and Docker compose files need a single source of truth under version control. Previously, files were scattered across `/mnt/shared/tmp/docker/`, `~/.hermes/scripts/`, `~/recon/`, and various deployment directories. SSH access was the only way to discover what ran where.

## Decision

Use a **single monorepo** at `~/projects/` pushed to `github.com/lenadlm/docker` with four top-level categories:

- `docker-stacks/` — compose files for all container stacks
- `automation/` — scripts, cron jobs, monitoring
- `infrastructure/` — host configs, network rules, Proxmox
- `notes/` — runbooks, ADRs, topology docs

Legacy files from the original repo (`gcp/`, `mpc/`, `pve/`, `tmp/`) are preserved but may be migrated into the new structure over time.

## Consequences

- ✅ Single `git pull` synchronises all infrastructure definitions
- ✅ `.env.example` pattern prevents secret leaks
- ✅ GPG-signed commits ensure audit trail
- ⚠️ Monorepo grows over time — `.gitignore` discipline required
- ⚠️ Docker host changes must be `scp`'d back or automated