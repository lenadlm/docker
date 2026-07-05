# Debugging ExtJS / Sencha Web Apps with Playwright

Enterprise apps (Ramco HCM, SAP Fiori, Oracle EBS, many HR/ERP portals) use
the ExtJS (Sencha) framework. ExtJS renders interactive elements as nested
`<span>` / `<a>` / `<div>` elements, **never** native HTML `<button>` or
`<input type="submit">` elements. Standard Playwright selectors for buttons
and form controls will silently fail to find anything.

## Detection: "Is this ExtJS?"

Look for these DOM signatures:

- Class names containing `x-btn`, `x-panel`, `x-window`, `x-border-item`
- Login button rendered as `<a class="x-btn ..."><span class="x-btn-wrap">
  <span class="x-btn-button"><span class="x-btn-inner">Login</span></span>
  </span></a>`
- Dynamic element IDs like `button-1159`, `button-1159-btnInnerEl`
- `<a>` tags with `role="button"` instead of native `<button>` elements
- Form fields that are `<input>` but with `disabled` / `readonly` attributes
  even though they appear editable

## Quick Probe (run inside container via `docker exec`)

```python
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    c = b.new_context(viewport={'width': 1920, 'height': 1080})
    p2 = c.new_page()
    p2.goto('<TARGET_URL>', wait_until='domcontentloaded', timeout=30000)
    p2.wait_for_load_state('networkidle', timeout=15000)
    p2.wait_for_timeout(3000)

    # Dump all x-btn anchors with text
    anchors = p2.eval_on_selector_all('a.x-btn',
        'els => els.filter(e => e.offsetParent !== null).map(e => ({id: e.id, text: e.innerText.trim()}))')
    print(f'Visible x-btn anchors ({len(anchors)}):')
    for a in anchors:
        print(f'  id={a["id"]}  text=\"{a["text"]}\"')

    # Find element containing specific text
    txt_els = p2.eval_on_selector_all(':not(script):not(style)',
        'els => els.filter(e => e.offsetParent !== null && e.children.length === 0 && e.innerText.trim() === "Login").map(e => ({t: e.tagName, id: e.id}))')
    print(f'Elements with exact text "Login" ({len(txt_els)}):')
    for el in txt_els:
        print(f'  tag={el["t"]} id={el["id"]}')

    b.close()
```

## Universal XPath Selector Pattern for ExtJS Buttons

ExtJS buttons always follow the pattern:

```
<a class="x-btn ...">
  <span class="x-btn-wrap">
    <span class="x-btn-button">
      <span class="x-btn-inner">VISIBLE TEXT</span>
    </span>
  </span>
</a>
```

Use this XPath to find the clickable `<a>` element by the visible button text:

```python
"xpath=//a[contains(@class, 'x-btn') and .//span[text()='BUTTON_TEXT']]"
```

Replace `BUTTON_TEXT` with the exact visible text: `Login`, `Ok`, `Cancel`,
`In`, `Out`, `Submit`, etc.

Place it **first** in your selector list so it's tried immediately:

```python
button_selectors = [
    "xpath=//a[contains(@class, 'x-btn') and .//span[text()='Login']]",  # ✓ ExtJS
    "button:has-text('Login')",   # fallback for non-ExtJS pages
    "input[value='Login']",       # fallback
]
```

## Password Field JS-Unlock Pattern

ExtJS often sets `disabled` or `readonly` on password fields even though they
appear editable. Playwright `fill()` will fail with "element is not editable".
Always unlock before filling:

```python
pwd = page.wait_for_selector("input[type='password']", timeout=15000)
disabled = pwd.get_attribute('disabled')
readonly = pwd.get_attribute('readonly')
if disabled or readonly:
    page.evaluate('el => { el.removeAttribute("disabled"); el.removeAttribute("readonly") }', pwd)
    page.wait_for_timeout(1000)
pwd.fill(PASSWORD)
```

## Complete Login Flow Pattern (ExtJS)

```python
# 1. Navigate
page.goto(url, wait_until='domcontentloaded', timeout=30000)
page.wait_for_load_state('networkidle', timeout=15000)

# 2. Fill username
page.wait_for_selector("input[placeholder='User Name']").fill(USERNAME)

# 3. Fill password (with JS unlock)
pwd = page.wait_for_selector("input[type='password']")
page.evaluate('el => { el.removeAttribute("disabled"); el.removeAttribute("readonly") }', pwd)
pwd.fill(PASSWORD)

# 4. Click login with XPath selector
page.locator("xpath=//a[contains(@class, 'x-btn') and .//span[text()='Login']]").click()

# 5. Handle post-login dialog (if any)
page.wait_for_timeout(5000)
ok_btn = page.locator("xpath=//a[contains(@class, 'x-btn') and .//span[text()='Ok']]")
if ok_btn.count() > 0 and ok_btn.first.is_visible():
    ok_btn.first.click()
    page.wait_for_timeout(3000)

# 6. Now on dashboard — apply same XPath pattern for IN/OUT buttons
```

## Dynamic IDs

ExtJS generates IDs like `button-1159`, `button-1646-btnIconEl`. These
CHANGE between page loads / sessions. NEVER hardcode them. Use XPath by
visible text + class.

**Exception — confirmed stable IDs:** Some ExtJS deployments use the same
IDs across page loads. If you've confirmed via repeated `docker exec` probes
that IDs are stable, you MAY use direct `#id` selectors for performance:

```python
# DOM-confirmed stable (this deployment):
login_selectors = [
    "#button-1159-btnInnerEl",            # Span with "Login" text
    "xpath=//a[contains(@class, 'x-btn') and .//span[text()='Login']]",  # Universal fallback
]
```

**Verify stability:** Run `docker exec <container> python -u main.py once in`
twice — if both succeed with the same ID selectors, they're stable for this
deployment. If IDs change after a container rebuild, fall back to XPath.

## Zero native `<button>` elements
- **Post-login dialogs**: After login, ExtJS often shows a popup (welcome message,
  notification, or account-locked message). Check for `.x-window.x-message-box`
  and dismiss with `Ok` / `Cancel` before proceeding.
- **Account lockout**: Repeated failed login attempts (e.g., from broken selectors
  causing retries) will lock the account. The lock message is: *"The User Account
  is locked. Please contact the Administrator."* Detection: look for `x-message-box`
  dialog with "locked" in the text. Mitigation: fix selectors first, then test,
  to avoid triggering lockout during debugging.
- **Loading spinners**: ExtJS shows animated loading spinners during AJAX calls.
  Use `page.wait_for_load_state('networkidle', timeout=15000)` before interacting
  with dynamic content.
- **`docker logs` outputs to stderr**: When writing Python scripts inside Docker
  containers that parse container logs via `subprocess.run("docker logs ...")`,
  `r.stdout` will be empty because Docker writes logs to stderr. Use
  `r.stdout.strip() or r.stderr.strip()` to capture output correctly.