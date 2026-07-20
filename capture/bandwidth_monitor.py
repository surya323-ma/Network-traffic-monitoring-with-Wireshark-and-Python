#!/usr/bin/env python3
"""
Bandwidth Usage Monitor - Capture Agent
Sniffs packets on your Wi-Fi/LAN interface and writes bytes-per-IP
data to InfluxDB every FLUSH_INTERVAL seconds.

MUST run on a machine sitting on your home network (not on Render/cloud) -
raw packet capture requires being physically on the LAN and root/admin
privileges.

Install deps:  pip install -r requirements.txt
Run:           sudo python3 bandwidth_monitor.py
"""

import os
import time
import threading
from collections import defaultdict

from scapy.all import sniff, IP
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# ---------------------------------------------------------------------
# Config - loaded from environment variables (see .env.example)
# ---------------------------------------------------------------------
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "YOUR_TOKEN_HERE")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "bandwidth")
IFACE = os.getenv("CAPTURE_IFACE") or None  # e.g. "wlan0", "en0"; None = auto
FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", "5"))  # seconds

# ---------------------------------------------------------------------
# Optional: map IP addresses to friendly device names.
# Check your router's DHCP client list (usually 192.168.1.1 or
# 192.168.0.1 in a browser) to find these mappings.
# ---------------------------------------------------------------------
DEVICE_NAMES = {
    # "192.168.1.10": "Living Room TV",
    # "192.168.1.14": "Mayank Laptop",
    # "192.168.1.20": "Mom Phone",
}

traffic_counts = defaultdict(int)
lock = threading.Lock()

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client.write_api(write_options=SYNCHRONOUS)


def resolve_name(ip: str) -> str:
    return DEVICE_NAMES.get(ip, ip)


def packet_callback(pkt):
    """Called for every captured packet."""
    if IP in pkt:
        src_ip = pkt[IP].src
        size = len(pkt)  # includes Ethernet/IP/TCP headers
        with lock:
            traffic_counts[src_ip] += size


def flush_to_influx():
    """Periodically push accumulated byte counts to InfluxDB."""
    while True:
        time.sleep(FLUSH_INTERVAL)
        with lock:
            if not traffic_counts:
                continue
            snapshot = dict(traffic_counts)
            traffic_counts.clear()

        points = []
        for ip, total_bytes in snapshot.items():
            point = (
                Point("bandwidth_usage")
                .tag("ip_address", ip)
                .tag("device_name", resolve_name(ip))
                .field("bytes", total_bytes)
                .field("bytes_per_sec", total_bytes / FLUSH_INTERVAL)
            )
            points.append(point)

        try:
            write_api.write(bucket=INFLUX_BUCKET, record=points)
            print(f"[{time.strftime('%H:%M:%S')}] Wrote {len(points)} points to InfluxDB")
        except Exception as e:
            print(f"[WARN] Failed to write to InfluxDB: {e}")


def main():
    flusher = threading.Thread(target=flush_to_influx, daemon=True)
    flusher.start()

    print("Bandwidth Monitor: capture shuru ho raha hai... (Ctrl+C se rokein)")
    print(f"Interface: {IFACE or 'auto-detect'}")
    print(f"Writing to InfluxDB at: {INFLUX_URL} (bucket={INFLUX_BUCKET})")

    sniff(
        iface=IFACE,
        prn=packet_callback,
        store=False,
    )


if __name__ == "__main__":
    main()
