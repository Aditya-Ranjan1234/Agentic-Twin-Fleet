"""UtilizationAgent – monitors fleet load/utilization and suggests balancing.
Currently uses simplistic rules as a placeholder for ML-based optimisation.
"""
import json
import os
from datetime import datetime
import random

import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fleet_metrics")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=30000)
write_api = client.write_api()

mqtt_client = mqtt.Client()

threshold_speed_low = float(os.getenv("UTIL_LOW_SPEED", "20"))  # km/h indicates idle


actions_topic_template = "fleet/action/{vehicle_id}/utilization"


def create_action(vehicle_id: str, reason: str):
    action = {
        "vehicle_id": vehicle_id,
        "agent": "UtilizationAgent",
        "type": "utilization_plan",
        "reason": reason,
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "suggestion": random.choice(["reassign_load", "combine_with_route", "shift_schedule"]),
    }
    mqtt_client.publish(actions_topic_template.format(vehicle_id=vehicle_id), json.dumps(action), qos=1)

    pt = (
        Point("agent_action")
        .tag("vehicle_id", vehicle_id)
        .tag("agent", "UtilizationAgent")
        .field("type", "utilization_plan")
        .field("reason", reason)
        .field("suggestion", action["suggestion"])
        .time(datetime.utcnow())
    )
    write_api.write(bucket=INFLUX_BUCKET, record=pt)

    print("[UtilizationAgent] action", action)


def on_connect(client, userdata, flags, rc):
    print("[UtilizationAgent] Connected", rc)
    client.subscribe("fleet/telemetry", qos=1)


def on_message(client, userdata, msg):
    try:
        telemetry = json.loads(msg.payload.decode())
        vehicle_id = telemetry.get("vehicle_id")
        speed = telemetry.get("speed")
        if speed is not None and speed < threshold_speed_low:
            create_action(vehicle_id, "low_speed_idle")
    except Exception as exc:
        print("[UtilizationAgent] error", exc)


def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, keepalive=60)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
