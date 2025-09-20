import cv2
import time
import json
import os
from pathlib import Path
from datetime import datetime

def atomic_write(path: Path, data: dict):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(str(tmp), str(path))

def read_status(path: Path):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return {}

def run(status_file: str, event_queue=None, poll_interval: float = 1.0, device_index: int = 0):
    """Continuously check camera availability and update status file. Put events on queue when state changes."""
    status_path = Path(status_file)
    last_connected = None

    while True:
        # Try opening the camera (on Windows CAP_DSHOW reduces delays)
        cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
        connected = cap.isOpened()
        if connected:
            # warm read (not saving frames)
            ret, _ = cap.read()
            if not ret:
                connected = False
        cap.release()

        data = read_status(status_path)
        cam_info = {"connected": bool(connected), "checked_at": datetime.utcnow().isoformat() + "Z"}
        data["camera"] = cam_info
        try:
            atomic_write(status_path, data)
        except Exception as e:
            print("camera write error:", e)

        if last_connected is None or connected != last_connected:
            last_connected = connected
            if event_queue is not None:
                event_queue.put({
                    "type": "camera",
                    "connected": bool(connected),
                    "when": cam_info["checked_at"]
                })
        time.sleep(poll_interval)

if __name__ == "__main__":
            run("utils/status.json")