# Recipe: Fixing Git Stash Errors during Hermes Update

## Problem
The `hermes update` command fails with a Git status 128 during the stash phase:
`✗ Update failed: Command '['git', 'rev-parse', '--verify', 'refs/stash']' returned non-zero exit status 128.`

This usually indicates untracked directories (like `tinker-atropos/`) or minor index corruption in the `~/.hermes/hermes-agent` repository.

## Remediation Steps

1. **Verify State**
   ```bash
   cd ~/.hermes/hermes-agent
   git status
   ```

2. **Force Reset to Origin**
   If you have no local changes you care about, perform a hard reset to the latest main branch.
   ```bash
   git fetch --all
   git reset --hard origin/main
   ```

3. **Cleanup Untracked Items**
   If the reset leaves directories behind that Git complained about:
   ```bash
   rm -rf <problem_directory>
   ```

4. **Retry Update**
   ```bash
   hermes update --yes
   ```

## Verification
Run `hermes status --all` to confirm the code is aligned with the latest version.
