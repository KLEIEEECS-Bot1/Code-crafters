import sounddevice as sd
import time
import json
import os
import signal
from pathlib import Path
from datetime import datetime

print("Using sounddevice mic_monitor.py")  # Confirm this file is running

# ======= Helpers =======

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

# ======= Global running flag =======
running = True

def handle_sigint(sig, frame):
    global running
    print("\nStopping microphone monitor...")
    running = False

signal.signal(signal.SIGINT, handle_sigint)

# ======= Microphone check =======

def check_input_devices():
    try:
        devices = sd.query_devices()
        for idx, info in enumerate(devices):
            if info["max_input_channels"] > 0:
                return True, {"name": info["name"], "index": idx}
    except Exception:
        return False, None
    return False, None

# ======= Monitor loop =======

def run(status_file: str, event_queue=None, poll_interval: float = 2.0):
    status_path = Path(status_file)
    Path(status_path.parent).mkdir(parents=True, exist_ok=True)  # ensure folder exists

    last_ok = None

    while running:
        ok, info = check_input_devices()

        data = read_status(status_path)
        mic_info = {"accessible": bool(ok), "checked_at": datetime.utcnow().isoformat() + "Z"}
        if info:
            mic_info["device"] = info
        data["microphone"] = mic_info

        try:
            atomic_write(status_path, data)
        except Exception as e:
            print("mic write error:", e)

        # Only trigger event if state changes
        if last_ok is None or ok != last_ok:
            last_ok = ok
            print(f"Microphone accessible: {ok}")
            if event_queue is not None:
                event_queue.put({
                    "type": "microphone",
                    "accessible": bool(ok),
                    "when": mic_info["checked_at"]
                })

        time.sleep(poll_interval)

    print("Microphone monitor stopped.")

# ======= Main =======
if __name__ == "__main__":
    run("utils/status.json")
