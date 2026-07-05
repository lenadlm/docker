# hlr-login (Playwright) Docker Deploy

Workflow for stopping, reconfiguring (`APP_PASSWORD`), rebuilding, and
redeploying the `hlr-login` container using raw Docker or docker compose.

## Location

Project root: `/docker/pyauto/playwright/`

Key files:
- `docker-compose.yml` — service definition (env vars: `APP_USERNAME`, `APP_PASSWORD`)
- `dockerfile` — build instructions (Playwright Python base)
- `main.py` — Playwright automation + scheduler (Mon-Sat IN/OUT)
- `txt` — raw Docker instructions (`docker build --no-cache -t hlr .`)

## Build & Deploy

### docker compose:
```bash
docker stop hlr-login && docker rm hlr-login
cd /docker/pyauto/playwright
sudo sed -i 's/APP_PASSWORD: ".*"/APP_PASSWORD: "NEW_VALUE"/' docker-compose.yml
sudo docker compose up --build -d
```

### raw Docker (preferred when `txt` file exists):
```bash
docker stop hlr-login && docker rm hlr-login
cd /docker/pyauto/playwright
sudo docker build --no-cache -t hlr .
docker run -d --name hlr-login --restart unless-stopped \
  -e APP_USERNAME="42830" -e APP_PASSWORD="VALUE" hlr
```

### manual runs (for testing):
```bash
docker exec hlr-login python main.py once in    # single IN (no retry)
docker exec hlr-login python main.py once out   # single OUT (no retry)
docker run --rm hlr in                           # ephemeral IN run
docker run --rm hlr out                          # ephemeral OUT run
```

## Logs & Debugging

### Check container logs:
```bash
docker logs hlr-login --tail 50
```

### Check scheduler jobs (inside container):
```bash
docker exec hlr-login python -c "import schedule; [print(j) for j in schedule.get_jobs()]"
```

### Active scheduler PID:
```bash
docker exec hlr-login ps aux | grep python
```

## Selector Evolution

### Phase 1: XPath fix (2026-06-08)

Added XPath selector for the ExtJS login `<a>` tag as first priority in
`login_selectors`. Solved login — but arrow + IN/OUT still failed with same
ExtJS `<button>` mismatch, and repeated retries locked the account.

### Phase 2: DOM-confirmed static IDs (2026-06-09)

Updated ALL selectors to use concrete DOM IDs discovered via live inspection
(`document.querySelector(...)`) inside the running container. These IDs are
stable across page loads for this specific deployment:

| Component | Working Selector | Type |
|-----------|-----------------|------|
| Login button | `#button-1159-btnInnerEl` | Span (ExtJS inner text holder) |
| Arrow panel | `#slidenext-button-1646-btnIconEl` | Span (fa-caret-right icon) |
| IN button | `#btnhrbook1_inbtn-button-1563-btnWrap` | Span (ExtJS outer wrap) |
| OUT button | `#btnhrbook1_out-button-1570-btnInnerEl` | Span (ExtJS inner text holder) |
| Username | `#ide_username-textfield-1155-inputEl` | Input (ExtJS textfield) |
| Password | `#ide_password-textfield-1156-inputEl` | Input (ExtJS textfield) |

**Performance:** Full IN automation completes in **~43s** (down from ~4min).

```log
Clicked Login button via selector: #button-1159-btnInnerEl
Clicked arrow button via selector: #slidenext-button-1646-btnIconEl
Clicked 'In' button via selector: #btnhrbook1_inbtn-button-1563-btnWrap
Action IN completed successfully
```

### When DOM IDs Change

If the ExtJS framework regenerates element IDs, fall back to the universal
XPath pattern from `references/extjs-playwright-debug.md`.

## Post-Login Dialog Handling

After login, ExtJS may show a popup with `Ok`/`Cancel` (welcome message,
notification, or account-locked message). Detect and dismiss:

```python
ok_btn = page.locator("xpath=//a[contains(@class, 'x-btn') and .//span[text()='Ok']]")
if ok_btn.count() > 0 and ok_btn.first.is_visible():
    ok_btn.first.click()
```

**Account locked message (detected 2026-06-08):**
*"The User Account is locked. Please contact the Administrator or click on
forgot password link for unlocking the account."*

Detection: look for `.x-window.x-message-box` dialog containing "locked".

## Account Lockout Risk

Each attempt runs 3 retries. With broken selectors, attempts take ~4min →
12+ rapid hits → account auto-locks. **Always fix selectors before
end-to-end testing.** Test each step individually with `once` mode.

## Health Monitoring

A dedicated health monitor (`~/.hermes/scripts/hlr_login_monitor.py`)
runs daily at 09:00 via cron job `0c28287aba47` (no_agent mode):

- Checks container status (running/stopped/uptime)
- Parses last 7 IN + 7 OUT automation runs from docker logs
- Reports success/failure per run with duration
- Analyzes failures with specific root causes and fix recommendations
- Health score 0-100 with emoji

```bash
# Manual run:
python3 ~/.hermes/scripts/hlr_login_monitor.py
```

**Note:** `docker logs` outputs to **stderr** (not stdout). Python scripts
must capture both: `stdout or stderr`.

## ExtJS Debugging Methodology

See `references/extjs-playwright-debug.md` for the full reusable technique:
detecting ExtJS pages, dumping page elements, building XPath selectors,
JS-unlocking disabled fields, and the complete login flow pattern.

## Other Pitfalls

- `docker-compose` (v1) may not exist — use `docker compose` (v2 plugin)
- `/docker/` requires `sudo` for writes — use `sudo sed` / `sudo tee`
- `--no-cache` for fresh build when source changes; omit for incremental
- `network_mode: bridge`; no port mapping; logs via `docker logs hlr-login`
- Password field needs JS unlock (`removeAttribute("disabled")` + `removeAttribute("readonly")`)
  before .fill() — ExtJS marks fields as non-editable even when visible
- Prefer `docker exec python main.py once <in|out>` over the full retry path
  when debugging — avoids triggering account lockout from repeated failures
- **Zombie prevention:** Added `init: true` to docker-compose.yml. This wraps the process with tini (/sbin/docker-init) which auto-reaps orphaned Playwright headless_shell children. Without it, 40+ zombies accumulated over 8 days.