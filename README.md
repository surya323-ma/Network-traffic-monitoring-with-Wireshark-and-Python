# Home Bandwidth Usage Monitor

Capture network traffic on your Wi-Fi, find out which device is eating
your bandwidth, and see it visualized live in Grafana.

## How it's split up (and why)

| Part | Where it runs | Why |
|---|---|---|
| `capture/` - Scapy packet sniffer | **Your home machine** (PC / laptop / Raspberry Pi, always-on) | Needs to physically sit on your Wi-Fi/LAN to see the packets. Cloud hosts like Render never see your home traffic, so this piece cannot be deployed there. |
| InfluxDB - stores bytes-per-device over time | Locally (Docker) **or** Render | Just a database, can live anywhere reachable from your capture agent. |
| Grafana - dashboard / pie chart | Locally (Docker) **or** Render | Just reads from InfluxDB, can live anywhere. |

So the realistic deployment is: **capture agent stays at home, InfluxDB +
Grafana get deployed to Render** so you can check the dashboard from your
phone/laptop from anywhere, with the home agent pushing data to it over
the internet.

If you'd rather keep everything fully local (no cloud, no Render), just
run `docker compose up` and skip the Render section entirely.

---

## Option 1: Fully local (easiest, good for testing)

```bash
git clone <your-repo-url>
cd bandwidth-monitor
cp .env.example .env
# edit .env if you want, defaults work fine for local testing

docker compose up -d influxdb grafana
docker compose --profile local-only up capture
```

- InfluxDB UI: http://localhost:8086
- Grafana UI: http://localhost:3000 (login: admin / admin, or whatever you set in `.env`)

Then import `dashboard/grafana-dashboard.json` into Grafana:
**Grafana → Dashboards → New → Import → Upload JSON file.**

You'll be asked to pick your InfluxDB data source (create one first: 
**Connections → Data sources → Add data source → InfluxDB**, query language
**Flux**, URL `http://influxdb:8086`, and your org/bucket/token from `.env`).

---

## Option 2: GitHub + Render (dashboard accessible from anywhere)

### Step 1 - Push to GitHub

```bash
cd bandwidth-monitor
git init
git add .
git commit -m "Initial commit: bandwidth monitor project"
git branch -M main
git remote add origin https://github.com/<your-username>/bandwidth-monitor.git
git push -u origin main
```

`.env` is git-ignored on purpose - never commit real tokens/passwords.

### Step 2 - Deploy InfluxDB + Grafana to Render

1. Go to [render.com](https://render.com) → **New → Blueprint**
2. Connect your GitHub account and select this repo
3. Render will read `render.yaml` and create two services:
   - `bandwidth-influxdb`
   - `bandwidth-grafana`
4. Render will prompt you to fill in the `sync: false` environment
   variables (usernames, passwords, tokens) - fill these in yourself,
   don't leave defaults.
5. Note: persistent disks (used here so your data survives restarts)
   require a paid Render plan, not the free tier.
6. Once deployed, Render gives each service a public URL like
   `https://bandwidth-grafana.onrender.com`

### Step 3 - Point your home capture agent at the deployed InfluxDB

On your home machine, edit `.env`:

```
INFLUX_URL=https://bandwidth-influxdb.onrender.com
INFLUX_TOKEN=<the token you set in Render>
INFLUX_ORG=home
INFLUX_BUCKET=bandwidth
```

Then run just the capture agent locally:

```bash
cd capture
pip install -r requirements.txt
sudo python3 bandwidth_monitor.py
```

(Or `docker compose --profile local-only up capture` from the repo root,
with the same `.env` values.)

### Step 4 - View your dashboard

Open your Render Grafana URL, add the InfluxDB data source (URL =
your Render InfluxDB URL), and import `dashboard/grafana-dashboard.json`
as in Option 1.

---

## Quick terminal report (no Grafana needed)

```bash
cd report
pip install influxdb-client
python3 cli_report.py
```

Prints a simple top-10 table of devices by total data used in the last
hour, straight in your terminal.

---

## Finding your device names

Raw IPs aren't very readable. Log into your router's admin page
(usually `192.168.1.1` or `192.168.0.1` in a browser) and look at the
DHCP client list - it usually shows device names next to IPs. Copy
those into the `DEVICE_NAMES` dict at the top of
`capture/bandwidth_monitor.py`.

---

## What you'll learn

- **Packet headers**: every packet you capture has Ethernet/IP/TCP
  headers wrapped around the actual data. `len(pkt)` in the script
  gives you the full on-the-wire size, which is what your router
  effectively bills against your usage too.
- **Data rate calculation**: the script buckets bytes over
  `FLUSH_INTERVAL` seconds and computes `bytes_per_sec = total_bytes /
  interval` - the same idea speed test tools use, just derived from
  raw packets instead of a synthetic download.

---

## Troubleshooting

- **"Permission denied" running the capture script** → run with `sudo`
  (Linux/Mac) or an Administrator terminal (Windows, with
  [Npcap](https://npcap.com/) installed).
- **No packets showing up** → your interface name is probably wrong.
  Find it with `ip a` (Linux), `ifconfig` (Mac), or `ipconfig`
  (Windows), then set `CAPTURE_IFACE` in `.env`.
- **Grafana panel is empty** → check the data source URL/org/token
  match what's in your capture agent's `.env`, and that the capture
  agent is actually running and printing "Wrote N points to InfluxDB".
