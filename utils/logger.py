import json
import time
from pathlib import Path

class JsonLogger:
    def __init__(self, filepath: str):
        self.path = Path(filepath)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: dict):
        event["timestamp"] = int(time.time() * 1000)
        with self.path.open("a") as f:
            f.write(json.dumps(event) + "\n")
