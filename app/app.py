import json
import logging
import os
import sys
import time
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        level = "WARN" if record.levelno == logging.WARNING else record.levelname
        return json.dumps(
            {
                "@timestamp": datetime.now(timezone.utc).isoformat(),
                "level": level,
                "service": {"name": os.getenv("APP_SERVICE_NAME", "quickbite-app")},
                "message": record.getMessage(),
            },
            ensure_ascii=False,
        )


logger = logging.getLogger("quickbite")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

interval = max(1.0, float(os.getenv("APP_LOG_INTERVAL_SECONDS", "5")))
messages = (
    (logging.INFO, "Periodic application health check completed"),
    (logging.WARNING, "Example warning event for log pipeline testing"),
    (logging.ERROR, "Example error event for log pipeline testing"),
)

while True:
    for level, message in messages:
        logger.log(level, message)
        time.sleep(interval)
