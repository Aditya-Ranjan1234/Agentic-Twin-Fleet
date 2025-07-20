"""RoutingAgent – placeholder implementation.
In a full system this agent would solve VRP problems using OR-Tools, factoring
vehicle health, traffic, and load. For now it simply listens to telemetry and
prints a heartbeat so the container stays healthy.
"""
import os
import time
import paho.mqtt.client as mqtt

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))

def on_connect(client, userdata, flags, rc):
    print("[RoutingAgent] Connected", rc)
    client.subscribe("fleet/telemetry", qos=0)

def on_message(client, userdata, msg):
    # Placeholder – in future parse telemetry and optimize routes
    pass

def main():
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT, keepalive=60)
    mqtt_client.loop_start()
    # Heartbeat
    try:
        while True:
            time.sleep(30)
            print("[RoutingAgent] alive")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
