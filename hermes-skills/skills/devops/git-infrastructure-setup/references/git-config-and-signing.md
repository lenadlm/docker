# Git Config & GPG Signing Setup

## Global Config (~/.gitconfig)

```ini
[user]
	name = leo
	email = lenadlm@outlook.com
	signingkey = <GPG_KEY_ID>
[commit]
	gpgsign = true
[tag]
	gpgsign = true
[init]
	defaultBranch = main
[pull]
	rebase = true
[push]
	autoSetupRemote = true
```

Set with:
```bash
git config --global user.name "leo"
git config --global user.email "lenadlm@outlook.com"
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global push.autoSetupRemote true
```

## System Config (/etc/gitconfig)

```ini
[core]
	editor = nano
	autocrlf = input
[merge]
	conflictstyle = zdiff3
	ff = only
[protocol]
	version = 2
[help]
	autocorrect = 10
```

Write with sudo:
```bash
sudo tee /etc/gitconfig > /dev/null << 'EOF'
[core]
	editor = nano
	autocrlf = input
[merge]
	conflictstyle = zdiff3
	ff = only
[protocol]
	version = 2
[help]
	autocorrect = 10
EOF
```

## GPG Signing Key Generation

Generate an RSA 4096 key non-interactively:

```bash
cat > /tmp/gpg-batch << 'GPGEOF'
%no-protection
%transient-key
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: Leo
Name-Email: lenadlm@outlook.com
Expire-Date: 0
GPGEOF

gpg --batch --generate-key /tmp/gpg-batch
```

Extract key ID and configure git:

```bash
KEYID=$(gpg --list-secret-keys --keyid-format=long | grep "^sec" | head -1 | awk '{print $2}' | cut -d'/' -f2)
git config --global user.signingkey "$KEYID"
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

## Verify Setup

```bash
# All configs
git config --list --show-origin

# Signing works
echo "test" | git commit-tree HEAD^{tree} -m "sign test"
# Should produce a signed commit object with no errors
git cat-file -p HEAD | head -3

# Verify key
gpg --list-secret-keys --keyid-format=long
```

## Notes

- Ed25519 keys are preferred but may not be supported by all GPG 2.4.x builds. RSA 4096 is universally compatible.
- `%no-protection` creates a key without a passphrase — no interactive prompts.
- `%transient-key` ensures the key doesn't need curation (no designated revocation).
- All commits will be automatically signed (`commit.gpgsign = true`).