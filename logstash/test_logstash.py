import json
import os
import socket


event = {
    "app_name": "storex-backend",
    "service": "storex-backend",
    "level": "INFO",
    "message": "Order created successfully",
    "order_id": 1001,
}

host = os.getenv("LOGSTASH_HOST", "localhost")

with socket.create_connection((host, 5000), timeout=10) as connection:
    connection.sendall((json.dumps(event) + "\n").encode("utf-8"))

print(f"JSON event sent to Logstash at {host}:5000")
