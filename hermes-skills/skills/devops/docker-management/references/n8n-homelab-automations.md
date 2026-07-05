# n8n Homelab Automation Ideas

A curated catalogue of 35+ n8n workflow ideas for the homelab at `192.168.1.0/24` with Proxmox VE, Docker, Home Assistant, OPNsense, and Tailscale.

## Categories

- [🔧 Homelab Automation](#-homelab-automation)
- [🏡 Home Assistant Bridge](#-home-assistant-bridge)
- [📊 Monitoring & Alerts](#-monitoring--alerts)
- [🎮 Fun / Media](#-fun--media)
- [🛡️ Security](#️-security)
- [🧠 AI & Local LLM](#-ai--local-llm)
- [🔗 Proxmox Power User](#-proxmox-power-user)
- [🌐 Network Engineering](#-network-engineering)
- [📁 NAS / Storage](#-nas--storage)
- [🤖 Pure Fun / Novelty](#-pure-fun--novelty)
- [⚡ Utility / Quality of Life](#-utility--quality-of-life)

---

## 🔧 Homelab Automation

### Smart Shutdown / Power Budget
When UPS battery drops below 20%, n8n sends a webhook to PVE host to gracefully shutdown non-critical VMs, then notifies via Telegram. Prevents dirty NAS shutdown.

**Triggers**: HA sensor (battery level), webhook from UPS  
**Actions**: PVE API → stop VMs, Telegram notification

### Auto-Scale VMs
If Docker host disk usage > 85%, trigger a Proxmox VM template clone with more storage. If idle for 6h, suspend the VM.

**Triggers**: Cron (every hour), SSH disk check  
**Actions**: PVE API → clone/suspend VM

### Backup Dashboard
Every morning, check Proxmox backup logs. If a backup failed, retry once, then notify. Bonus: weekly "all clear" report.

**Triggers**: Cron (daily)  
**Actions**: PVE API → check backups → retry on failure → Telegram

### Let's Encrypt Alert
Scrape SSL cert expiry for all services. Notify 14, 7, and 3 days before expiry.

**Triggers**: Cron (daily)  
**Actions**: Fetch cert info from each service → check expiry → Telegram alert

---

## 🏡 Home Assistant Bridge

### Presence-Aware Wake-on-LAN
When you arrive home (HA detects phone on WiFi), n8n fires WoL packets to media server or gaming PC. Leave → suspend them.

**Triggers**: HA state change (person home/away)  
**Actions**: SSH → `wakeonlan` / `pm-suspend`

### Weather-Aware Backup
If HA says storm incoming, delay scheduled backups and notify. Resume when clear.

**Triggers**: HA weather sensor  
**Actions**: Pause/resume cron jobs, Telegram notification

### Doorbell → AI Alert
When doorbell pressed, n8n takes camera snapshot, sends to AI vision model (LLaVA/CLIP) to identify who's there, then DMs you.

**Triggers**: HA doorbell event  
**Actions**: HA camera snapshot → local LLM vision → Telegram with image + analysis

---

## 📊 Monitoring & Alerts

### Availability Pinger
Ping all core hosts (router, PVE, Docker, HA) every 5 min. If one misses 3 checks, alert on Telegram.

**Triggers**: Cron (5 min)  
**Actions**: ping/SSH check → Telegram alert

### Daily Health Dashboard
Collect CPU/RAM/disk from all hosts via SSH or SNMP, format as markdown, send to Telegram every morning.

**Triggers**: Cron (daily 8 AM)  
**Actions**: SSH → gather metrics → format → Telegram

### Docker Update Watcher
Check for updated Docker images nightly. If new versions exist, pull, restart stack, report changes.

**Triggers**: Cron (nightly)  
**Actions**: `docker compose pull` → `docker compose up -d` → Telegram diff

---

## 🎮 Fun / Media

### IMDB Watchlist Notifier
Keep a Google Sheets watchlist. When movie becomes available on Jellyfin/Plex, n8n sends "Ready to watch!" alert.

**Triggers**: Cron (daily)  
**Actions**: Check Plex/Jellyfin API → check Google Sheets → Telegram

### Bandwidth Hogs Alert
If OPNsense reports a device using > 50GB in a day, send hostname and usage.

**Triggers**: Cron (daily)  
**Actions**: OPNsense API → filter top users → Telegram

### Random Dinner Decider
Keep a recipe list. Every Friday 6PM, pick one and text. Bonus: check ingredients in grocery DB.

**Triggers**: Cron (weekly)  
**Actions**: Random selection → Telegram

---

## 🛡️ Security

### SSH Attack Reporter
Poll `journalctl -u ssh` or OPNsense firewall logs for brute force attempts. >10 failed logins from one IP in 5 min = add to blocklist.

**Triggers**: Cron (5 min)  
**Actions**: Parse logs → check threshold → block IP via OPNsense → Telegram

### Cloudflare Tunnel Health
Check if Cloudflare tunnels are up. If a service goes offline externally, restart tunnel and warn.

**Triggers**: Cron (10 min)  
**Actions**: HTTP check via CF domain → `docker compose restart cloudflared` → Telegram

### New Device Detection
Poll OPNsense DHCP leases. New MAC not in known-devices list → do ARP/mDNS lookup → ask Telegram if you want to tag/block.

**Triggers**: Cron (15 min)  
**Actions**: OPNsense API → diff against known MACs → Telegram with description

---

## 🧠 AI & Local LLM

### AI-Powered Email Filter
n8n watches IMAP inbox. New email → send to local Ollama LLM: "Urgent, newsletter, spam, or personal?" → tag/archive/notify.

**Triggers**: IMAP polling (5 min)  
**Actions**: Fetch email → LLM classify → IMAP move → Telegram

### Daily Homelab Digest (AI-written)
Every 7 AM, collect PVE host metrics, Docker status, OPNsense blocked attempts, HA sensors. Feed to LLM: "Summarise as a brief, slightly sarcastic operations report." Deliver to Telegram.

**Triggers**: Cron (daily 7 AM)  
**Actions**: SSH collect → LLM summarise → Telegram

### SMS/Telegram Buddy
You text a question → n8n fetches HA weather + Google Calendar → LLM produces natural reply → texts back.

**Triggers**: Telegram message from you  
**Actions**: Fetch context → LLM compose → reply

---

## 🔗 Proxmox Power User

### One-Click Dev Environment
Send `/dev` to Telegram → n8n clones PVE VM template, boots it, runs Ansible to install dev tools, texts you the IP.

**Triggers**: Telegram command `/dev`  
**Actions**: PVE API → clone → start → Ansible → Telegram

### Snapshot Scheduler with Notifications
Before `apt upgrade`, n8n snapshots all VMs, runs update, notifies. If breakage, rollback instructions included.

**Triggers**: Webhook (manual), cron (scheduled updates)  
**Actions**: PVE API → snapshot → run update → Telegram

### VM Resource Whiner
Every hour, check PVE for VMs with far more assigned resources than used. Send "You're wasting resources" message.

**Triggers**: Cron (hourly)  
**Actions**: PVE API → compare assigned vs used → Telegram

---

## 🌐 Network Engineering

### Bandwidth Report Card
Every Sunday, grab per-device bandwidth from OPNsense. Top 3 data hogs get called out.

**Triggers**: Cron (weekly)  
**Actions**: OPNsense API → sort → Telegram with emoji commentary

### Dynamic DNS Failover
If Cloudflare reports public IP changed, update DNS records, restart CF tunnels, verify all services reachable.

**Triggers**: Cron (5 min)  
**Actions**: Check CF API → compare IP → update DNS → verify tunnels

### Tailscale Peer Watcher
Check Tailscale network every 10 min. Peer offline > 1h = Telegram alert.

**Triggers**: Cron (10 min)  
**Actions**: `tailscale status --json` → check peers → Telegram

---

## 📁 NAS / Storage

### Duplicate File Hunter
SSH into NAS, run `fdupes` weekly, send report with paths and wasted space.

**Triggers**: Cron (weekly)  
**Actions**: SSH → `fdupes` → format → Telegram

### Disk Space Prophet
Track NAS disk usage daily for 30 days. Run linear regression to predict exhaustion date.

**Triggers**: Cron (daily)  
**Actions**: SSH → `df` → store in InfluxDB/local → predict → Telegram when < 30 days

### Photo Gallery Auto-Tagging
New photos in NAS folder → trigger local vision model (LLaVA/CLIP) to generate descriptions/tags.

**Triggers**: INotify/webhook on NAS → n8n  
**Actions**: Run vision model → update metadata DB

---

## 🤖 Pure Fun / Novelty

### Homelab Rap Battle
Every Friday, collect metrics, feed to LLM: "Write a 30-second rap celebrating this week's homelab victories." Send as TTS voice note.

**Triggers**: Cron (weekly Friday)  
**Actions**: Gather metrics → LLM rap → TTS → Telegram voice

### Status Page
n8n powers a simple public HTML page showing: ☑️ Internet / 🟢 Proxmox / 🔴 Docker. Updated every 60s.

**Triggers**: Cron (1 min)  
**Actions**: Health checks → write HTML file → serve via nginx

### Screencap of the Day
SSH into Ubuntu VM, run `neofetch` + `docker ps` + `df -h`, capture as image, send to Telegram.

**Triggers**: Cron (daily)  
**Actions**: SSH → terminal recording → send image

---

## ⚡ Utility / Quality of Life

### GitHub Push Deployer
Push to `docker` repo → GitHub webhook → n8n pulls new compose files on Docker host → diffs running stack → deploys only changed services.

**Triggers**: GitHub webhook  
**Actions**: `git pull` → `docker compose up -d` on changed services

### Password Rotation Cop
Track when each service password was last changed. At day 85 → remind. At day 95 → generate new one, update `.env`, text you.

**Triggers**: Cron (daily)  
**Actions**: Check password age → remind/rotate → Telegram

### Cost of Electricity Tracker
Read PVE host power consumption via IPMI/sensors, multiply by kWh rate, report monthly cost.

**Triggers**: Cron (daily + monthly summary)  
**Actions**: IPMI/sensor read → calculate → Telegram

---

## Implementation Notes

- **n8n webhook URLs**: Use `http://192.168.1.220:5678/webhook/<id>` for local triggers
- **SSH nodes**: n8n's SSH node can execute commands on any Linux host
- **HTTP Request nodes**: Use for Proxmox API (port 8006), HA API (port 8123), OPNsense API
- **Telegram nodes**: n8n has native Telegram trigger + action nodes
- **Cron trigger**: n8n's built-in schedule trigger supports cron expressions
- **Variables**: Use n8n Variables for shared config (IPs, credentials)
- **Error workflows**: Create a dedicated error-handler workflow that catches failures from all others