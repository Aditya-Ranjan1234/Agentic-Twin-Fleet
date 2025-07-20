"""Flask API & Dashboard server for Agentic Twin Fleet Manager."""
import os
from functools import lru_cache
from datetime import datetime

from flask import Flask, jsonify, render_template
from influxdb_client import InfluxDBClient
import pandas as pd

app = Flask(__name__, template_folder="templates", static_folder="static")

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fleet_metrics")


@lru_cache()
def get_influx_client():
    return InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=30000)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/vehicles")
def api_vehicles():
    query_api = get_influx_client().query_api()
    query = f"""
    from(bucket: \"{INFLUX_BUCKET}\")
      |> range(start: -10m)
      |> filter(fn: (r) => r._measurement == \"vehicle_telemetry\")
      |> last()
    """
    tables = query_api.query(query)
    latest = []
    for table in tables:
        vehicle_id = table.records[0].values.get("vehicle_id")
        recs = {r.get_field(): r.get_value() for r in table.records}
        recs["vehicle_id"] = vehicle_id
        recs["timestamp"] = table.records[0].get_time().isoformat()
        latest.append(recs)
    return jsonify(latest)


@app.route("/api/vehicle/<vehicle_id>/timeseries")
def api_vehicle_timeseries(vehicle_id):
    # Return last 1h of data for a given vehicle_id
    query_api = get_influx_client().query_api()
    query = f"""
    from(bucket: \"{INFLUX_BUCKET}\")
      |> range(start: -1h)
      |> filter(fn: (r) => r._measurement == \"vehicle_telemetry\" and r.vehicle_id == \"{vehicle_id}\")
    """
    df = query_api.query_data_frame(query)
    if df.empty:
        return jsonify([])
    df = (
        df[["_time", "_field", "_value"]]
        .pivot(index="_time", columns="_field", values="_value")
        .reset_index()
    )
    df["_time"] = df["_time"].astype(str)
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/actions")
def api_actions():
    """Return recent agent actions (last 100) for dashboard."""
    query_api = get_influx_client().query_api()
    query = f"""
    from(bucket: \"{INFLUX_BUCKET}\")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == \"agent_action\")
      |> sort(columns: [\"_time\"], desc: true)
      |> limit(n: 100)
    """
    tables = query_api.query(query)
    actions = []
    for table in tables:
        for record in table.records:
            actions.append({
                "time": record.get_time().isoformat(),
                "vehicle_id": record.values.get("vehicle_id"),
                "agent": record.values.get("agent"),
                "type": record.values.get("type"),
                "issue": record.values.get("issue"),
                "value": record.values.get("value"),
            })
    return jsonify(actions)



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
