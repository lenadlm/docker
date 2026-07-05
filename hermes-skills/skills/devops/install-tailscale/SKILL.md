---
name: install-tailscale
description: Install Tailscale on Ubuntu/Debian hosts when standard apt and install script methods fail or time out.
version: 1.0.0
---

# Install Tailscale via apt (manual repo setup)

## When to use
- `sudo apt-get install tailscale` fails with "Unable to locate package"
- `curl https://tailscale.com/install.sh | sh` times out or gets blocked
- GitHub releases page returns 0 assets (Tailscale doesn't ship deb files via GitHub)

## Steps

1. **Download GPG key** (save to /tmp first, avoid direct sudo tee which can timeout):
   ```bash
   curl -fsSL --retry 3 --retry-delay 2 --max-time 30 https://pkgs.tailscale.com/stable/ubuntu/$(grep UBUNTU_CODENAME /etc/os-release | cut -d= -f2).noarmor.gpg -o /tmp/tailscale.gpg
   ```

2. **Install the keyring**:
   ```bash
   sudo mkdir -p /usr/share/keyrings
   sudo cp /tmp/tailscale.gpg /usr/share/keyrings/tailscale-archive-keyring.gpg
   sudo chmod 644 /usr/share/keyrings/tailscale-archive-keyring.gpg
   ```

3. **Add the apt source** (use `dd` instead of heredoc — heredocs can block/timeout):
   ```bash
   echo "deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/ubuntu $(lsb_release -cs) main" | sudo dd of=/etc/apt/sources.list.d/tailscale.list status=none
   ```

4. **Update and install**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y tailscale
   ```

5. **Enable and run**:
   ```bash
   sudo systemctl enable --now tailscaled
   sudo tailscale up
   ```

6. **Grab the auth URL** from the output — it looks like `https://login.tailscale.com/a/<token>`

## For other distros
- **Fedora/RHEL/CentOS**: Use the `.repo` method from pkgs.tailscale.com
- **Arch**: Use AUR `tailscale` package
- **Static binary**: Extract from `https://github.com/tailscale/tailscale/releases/latest` tarball (but Tailscale no longer ships standalone tars in GitHub releases — use apt/yum instead)

## Pitfalls
- Tailscale does NOT ship .deb files on GitHub releases (0 assets)
- The `install.sh` script often times out when downloading large files interactively
- Heredocs (`cat << 'EOF' | sudo tee ...`) can block/timout — use `echo | sudo dd` instead
- Verify the codename from `/etc/os-release` (`UBUNTU_CODENAME` or `VERSION_CODENAME`) before using it in the URL
