import json
import os
import socket
import sys


events = [
    {
        "app_name": "user-service",
        "level": "INFO",
        "message": "User login successfully",
        "user_id": 101,
    },
    {
        "app_name": "user-service",
        "level": "WARN",
        "message": "User login failed",
        "user_id": 102,
    },
    {
        "app_name": "order-service",
        "level": "INFO",
        "message": "Order created successfully",
        "order_id": 1001,
    },
    {
        "app_name": "order-service",
        "level": "ERROR",
        "message": "Order processing failed",
        "order_id": 1002,
    },
]

host = os.getenv("LOGSTASH_HOST", "localhost")

try:
    with socket.create_connection((host, 5000), timeout=10) as connection:
        for event in events:
            connection.sendall((json.dumps(event) + "\n").encode("utf-8"))
            print(f"Sent {event['app_name']} event: {event['message']}")
except OSError as error:
    print(f"Could not send test events to {host}:5000: {error}", file=sys.stderr)
    sys.exit(1)

print(f"Successfully sent {len(events)} JSON Lines events to {host}:5000")
