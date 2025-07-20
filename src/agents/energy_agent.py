"""EnergyAgent – watches fuel_level and suggests refuelling/charging schedule."""
import json
import os
from datetime import datetime

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

LOW_FUEL_LEVEL = float(os.getenv("LOW_FUEL_LEVEL", "15"))

actions_topic_template = "fleet/action/{vehicle_id}/energy"


def create_action(vehicle_id: str, level: float):
    action = {
        "vehicle_id": vehicle_id,
        "agent": "EnergyAgent",
        "type": "charge_schedule",
        "fuel_level": level,
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "schedule": "nearest_station",
    }
    mqtt_client.publish(actions_topic_template.format(vehicle_id=vehicle_id), json.dumps(action), qos=1)

    pt = (
        Point("agent_action")
        .tag("vehicle_id", vehicle_id)
        .tag("agent", "EnergyAgent")
        .field("type", "charge_schedule")
        .field("fuel_level", level)
        .time(datetime.utcnow())
    )
    write_api.write(bucket=INFLUX_BUCKET, record=pt)

    print("[EnergyAgent] action", action)


def on_connect(client, userdata, flags, rc):
    print("[EnergyAgent] Connected", rc)
    client.subscribe("fleet/telemetry", qos=1)


def on_message(client, userdata, msg):
    try:
        telemetry = json.loads(msg.payload.decode())
        vehicle_id = telemetry.get("vehicle_id")
        fuel_level = telemetry.get("fuel_level")
        if fuel_level is not None and fuel_level < LOW_FUEL_LEVEL:
            create_action(vehicle_id, fuel_level)
    except Exception as exc:
        print("[EnergyAgent] error", exc)


def main():
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, keepalive=60)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
