import paho.mqtt.client as mqtt
import json
from typing import Optional
import threading
import queue


class MQTTService:
    def __init__(self, broker: str = "localhost", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = None
        self.latest_data = None
        self.data_queue = queue.Queue()
        self.lock = threading.Lock()
        self.connected = False

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"✓ MQTT Connected to {self.broker}:{self.port}")
            self.connected = True
            client.subscribe("data")
            print("✓ Subscribed to topic 'data'")
        else:
            print(f"✗ MQTT Connection failed: {rc}")
            self.connected = False

    def on_message(self, client, userdata, msg):
        try:
            print(f"📨 MQTT Message received on topic '{msg.topic}'")
            data = json.loads(msg.payload.decode())
            print(f"📊 Data: {data}")

            with self.lock:
                self.latest_data = data
                self.data_queue.put(data)
                print(f"✅ Data queued for streaming")
        except Exception as e:
            print(f"✗ Error processing message: {e}")

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            print(f"⚠ Unexpected MQTT disconnection. Code: {rc}")

    def start(self):
        try:
            print(f"🚀 Starting MQTT Service...")
            print(f"   Broker: {self.broker}:{self.port}")

            self.client = mqtt.Client(client_id="fastapi_sse_server")
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            self.client.on_disconnect = self.on_disconnect

            print(f"🔌 Connecting to MQTT broker...")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            print(f"✓ MQTT loop started")
        except Exception as e:
            print(f"✗ Error starting MQTT service: {e}")

    def stop(self):
        print("🛑 Stopping MQTT Service...")
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        print("✓ MQTT Service stopped")

    def get_latest_data(self) -> Optional[dict]:
        with self.lock:
            return self.latest_data

    def get_data_blocking(self, timeout=30):
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None


mqtt_service = MQTTService()
