#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import sys

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyZTg5ZGRkMDA2MGY0MTZiOGMyMWVhNjMyYWI5ZTJiNiIsImlhdCI6MTc3NTg4MTA2MiwiZXhwIjoyMDkxMjQxMDYyfQ.Vpb_vDqO2mu12zQ1Shz83meUCdYZ1596zv_6YuHjzBA"
URL = "http://192.168.1.123:8123/api/states/update.home_assistant_core_update"
TELEGRAM_BOT_TOKEN = "BOT_ID_REDACTED:AAE_UkuF3CytuP38Az8-EuCY4QdCme8Qd6g"
TELEGRAM_CHAT_ID = "CHAT_ID_REDACTED"

def send_telegram(message):
    import urllib.parse
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        data=data,
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)

def main():
    req = urllib.request.Request(URL)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except urllib.error.URLError as e:
        send_telegram(f"❌ Home Assistant update check failed: {e}")
        return 1
    
    entity = data
    installed = entity.get("attributes", {}).get("installed_version")
    latest = entity.get("attributes", {}).get("latest_version")
    in_progress = entity.get("attributes", {}).get("in_progress", False)
    percent = entity.get("attributes", {}).get("update_percentage")
    
    if installed == latest and not in_progress:
        send_telegram(f"✅ Home Assistant Core update completed successfully!\nInstalled: {installed}")
        return 0
    elif in_progress:
        send_telegram(f"🔄 Home Assistant Core update in progress: {percent}%\nCurrent: {installed} → Target: {latest}")
        return 0
    else:
        send_telegram(f"⚠️ Home Assistant Core update pending\nCurrent: {installed} → Latest: {latest}")
        return 0

if __name__ == "__main__":
    sys.exit(main())