#!/usr/bin/env python3
"""
Quick terminal report: top bandwidth-consuming devices from InfluxDB.

Install deps: pip install influxdb-client
Run:          python3 cli_report.py
"""

import os
from influxdb_client import InfluxDBClient

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "YOUR_TOKEN_HERE")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "bandwidth")


def report(hours=1, top_n=10):
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()

    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{hours}h)
      |> filter(fn: (r) => r._measurement == "bandwidth_usage")
      |> filter(fn: (r) => r._field == "bytes")
      |> group(columns: ["device_name"])
      |> sum()
      |> group()
      |> sort(columns: ["_value"], desc: true)
      |> limit(n: {top_n})
    '''

    tables = query_api.query(flux)

    print(f"\nTop {top_n} bandwidth consumers (last {hours}h)")
    print(f"{'Device':<25}{'Total Data':>15}")
    print("-" * 40)

    for table in tables:
        for record in table.records:
            device = record.values.get("device_name", "unknown")
            total_bytes = record.get_value()
            mb = total_bytes / (1024 * 1024)
            print(f"{device:<25}{mb:>12.2f} MB")

    client.close()


if __name__ == "__main__":
    report()
