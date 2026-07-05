# Host Diagnostics & Performance Recipes

## Large File Discovery
When scanning for large files on a host, avoid wide `find /` commands in the foreground as they frequently hit the 600s timeout in restricted environments.

### Scoped Python Scanner (Recommended)
This approach is robust to spaces in paths and avoids shell pipe overhead.
```python
import os
threshold = 100 * 1024 * 1024  # 100 MB
root = os.path.expanduser("~")
results = []
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        p = os.path.join(dirpath, f)
        try:
            sz = os.path.getsize(p)
            if sz > threshold:
                results.append((sz, p))
        except OSError: continue
results.sort(reverse=True)
for sz, p in results[:50]:
    print(f"{sz/1024/1024:.2f} MB\t{p}")
```

### Background Shell Scanner
If a host-wide scan is strictly necessary, run it as a background process with a redirect to a log file.
```bash
# Background task with notification on complete
# find / -xdev prevents crossing into network/special filesystems
find / -xdev -type f -size +100M -printf "%s\t%p\n" 2>/dev/null | sort -nr > /tmp/large_files.log
```

## Service Triage (cloudflared / QUIC)
When seeing "failed to accept QUIC stream" or "timeout: no recent network activity" in tunnel logs:
1. **QUIC Outbound**: Verify UDP port 443 and ephemeral UDP ports are not blocked by host or ISP firewalls.
2. **TCP Fallback**: If QUIC is unstable, update config to force protocol:
   ```yaml
   protocol: http2
   ```
3. **Binary Version**: Ensure the binary is current; Cloudflare edge frequently drops connections from very old clients.
