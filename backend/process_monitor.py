# backend/process_monitor.py
import psutil
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

def get_top_processes(limit=5):
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "username"]):
        try:
            procs.append(p.info)
        except Exception:
            pass
    # sort by CPU descending
    procs = sorted(procs, key=lambda x: x.get("cpu_percent", 0) or 0, reverse=True)
    return procs[:limit]

def run(status_file: str, event_queue=None, poll_interval: float = 5.0):
    status_path = Path(status_file)
    last_snapshot = None
    # initial cpu percent collection
    for p in psutil.process_iter():
        try:
            p.cpu_percent(interval=None)
        except Exception:
            pass

    while True:
        top = get_top_processes(7)
        snapshot = {"when": datetime.utcnow().isoformat() + "Z", "top": top}
        data = read_status(status_path)
        data["processes"] = snapshot
        try:
            atomic_write(status_path, data)
        except Exception as e:
            print("process write error:", e)

        # simple event example: if we see a new top process we can notify
        if last_snapshot is not None:
            last_names = {p["name"] for p in last_snapshot.get("top", []) if p.get("name")}
            curr_names = {p["name"] for p in top if p.get("name")}
            new = curr_names - last_names
            if new and event_queue is not None:
                event_queue.put({"type": "process", "new_top": list(new), "when": snapshot["when"]})
        last_snapshot = snapshot

        time.sleep(poll_interval)

if __name__ == "__main__":
    run("utils/status.json")
