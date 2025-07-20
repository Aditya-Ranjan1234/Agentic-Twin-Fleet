"""ReportingAgent – periodically aggregates recent actions and logs summary.
This is a background job writing a single Influx point every 10 minutes that
contains counts per agent type. In a full implementation it would generate
PDF/Email reports.
"""
import os
import time
from datetime import datetime, timedelta

from influxdb_client import InfluxDBClient, Point

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fleet_metrics")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=30000)
write_api = client.write_api()
query_api = client.query_api()

AGG_INTERVAL = int(os.getenv("REPORT_INTERVAL_SEC", "600"))

def aggregate_and_write():
    since = datetime.utcnow() - timedelta(seconds=AGG_INTERVAL)
    flux_query = f"""
    from(bucket: \"{INFLUX_BUCKET}\")
      |> range(start: {since.isoformat()}Z)
      |> filter(fn: (r) => r._measurement == \"agent_action\")
      |> group(columns: [\"agent\"])
      |> count()
    """
    tables = query_api.query(flux_query)
    for table in tables:
        agent = table.records[0].values.get("agent")
        count = table.records[0].get_value()
        pt = (
            Point("agent_summary")
            .tag("agent", agent)
            .field("count", int(count))
            .time(datetime.utcnow())
        )
        write_api.write(bucket=INFLUX_BUCKET, record=pt)
        print(f"[ReportingAgent] Summary {agent}: {count}")


def main():
    print("[ReportingAgent] started, interval", AGG_INTERVAL)
    while True:
        try:
            aggregate_and_write()
        except Exception as exc:
            print("[ReportingAgent] error", exc)
        time.sleep(AGG_INTERVAL)


if __name__ == "__main__":
    main()
