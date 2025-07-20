"""MQTT subscriber → writes telemetry into InfluxDB bucket.
"""
import os
import json
from datetime import datetime

from influxdb_client import InfluxDBClient, Point
import paho.mqtt.client as mqtt

# Environment variables
BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "")  # For local dev, may be empty if auth disabled
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "fleet_metrics")

client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=30000)
write_api = client.write_api()


def on_connect(mqtt_client, userdata, flags, rc):
    print("Connected to MQTT broker", rc)
    mqtt_client.subscribe("fleet/telemetry", qos=1)


def on_message(mqtt_client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        ts = datetime.utcfromtimestamp(data["timestamp"] / 1000.0)
        point = (
            Point("vehicle_telemetry")
            .tag("vehicle_id", data["vehicle_id"])
            .field("speed", float(data["speed"]))
            .field("engine_temp", float(data["engine_temp"]))
            .field("fuel_level", float(data["fuel_level"]))
            .field("tire_pressure", float(data["tire_pressure"]))
            .time(ts)
        )
        write_api.write(bucket=INFLUX_BUCKET, record=point)
    except Exception as exc:
        print("Failed to process message", exc)


def main():
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, keepalive=60)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
