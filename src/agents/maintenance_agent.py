"""MaintenanceAgent subscribes to vehicle telemetry and raises maintenance
recommendations based on simple rule thresholds. Both MQTT and InfluxDB are
used for I/O so everything is observable by other services and the dashboard.
"""
import json
import os
from datetime import datetime

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point

# Thresholds (can be tuned via env vars)
HIGH_ENGINE_TEMP = float(os.getenv("HIGH_ENGINE_TEMP", "95"))  # °C
LOW_TIRE_PRESSURE = float(os.getenv("LOW_TIRE_PRESSURE", "32"))  # PSI
LOW_FUEL_LEVEL = float(os.getenv("LOW_FUEL_LEVEL", "15"))  # %

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fleet_metrics")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=30000)
write_api = client.write_api()

mqtt_client = mqtt.Client()

actions_topic_template = "fleet/action/{vehicle_id}/maintenance"

def create_action(vehicle_id: str, issue: str, value: float):
    """Create action dict and write to InfluxDB."""
    action = {
        "vehicle_id": vehicle_id,
        "agent": "MaintenanceAgent",
        "type": "maintenance_request",
        "issue": issue,
        "value": value,
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
    }

    # Publish via MQTT so other systems can react
    mqtt_topic = actions_topic_template.format(vehicle_id=vehicle_id)
    mqtt_client.publish(mqtt_topic, json.dumps(action), qos=1)

    # Persist to Influx for dashboard/history
    pt = (
        Point("agent_action")
        .tag("vehicle_id", vehicle_id)
        .tag("agent", "MaintenanceAgent")
        .field("type", "maintenance_request")
        .field("issue", issue)
        .field("value", value)
        .time(datetime.utcnow())
    )
    write_api.write(bucket=INFLUX_BUCKET, record=pt)

    print("[MaintenanceAgent] action", action)


def on_connect(client, userdata, flags, rc):
    print("[MaintenanceAgent] Connected to MQTT", rc)
    client.subscribe("fleet/telemetry", qos=1)


def on_message(client, userdata, msg):
    try:
        telemetry = json.loads(msg.payload.decode())
        vehicle_id = telemetry.get("vehicle_id")
        engine_temp = telemetry.get("engine_temp")
        tire_pressure = telemetry.get("tire_pressure")
        fuel_level = telemetry.get("fuel_level")

        if engine_temp is not None and engine_temp > HIGH_ENGINE_TEMP:
            create_action(vehicle_id, "high_engine_temp", engine_temp)
        if tire_pressure is not None and tire_pressure < LOW_TIRE_PRESSURE:
            create_action(vehicle_id, "low_tire_pressure", tire_pressure)
        if fuel_level is not None and fuel_level < LOW_FUEL_LEVEL:
            create_action(vehicle_id, "low_fuel_level", fuel_level)
    except Exception as exc:
        print("[MaintenanceAgent] Failed to process telemetry", exc)


def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, keepalive=60)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
