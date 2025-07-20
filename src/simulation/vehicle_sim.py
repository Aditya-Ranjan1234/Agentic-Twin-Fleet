"""Simple vehicle telemetry simulator.
Publishes random telemetry JSON messages to MQTT topic `fleet/telemetry`.
"""
import os
import json
import time
import random
import paho.mqtt.client as mqtt

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
VEHICLE_ID = os.getenv("VEHICLE_ID", "vehicle-1")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL", "2"))  # seconds

client = mqtt.Client()
client.connect(BROKER, PORT, keepalive=60)
client.loop_start()

try:
    while True:
        payload = {
            "vehicle_id": VEHICLE_ID,
            "timestamp": int(time.time() * 1000),
            "speed": round(random.uniform(50, 80), 2),  # km/h
            "engine_temp": round(random.uniform(70, 100), 1),  # °C
            "fuel_level": round(random.uniform(10, 100), 1),  # %
            "tire_pressure": round(random.uniform(30, 35), 1),  # PSI
        }
        client.publish("fleet/telemetry", json.dumps(payload), qos=1)
        time.sleep(PUBLISH_INTERVAL)
except KeyboardInterrupt:
    print("Simulator stopped by user")
finally:
    client.loop_stop()
    client.disconnect()
