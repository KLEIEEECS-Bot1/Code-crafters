# main.py
import backend.mic_monitor
print("Mic monitor path:", backend.mic_monitor.__file__)

import multiprocessing
import subprocess
import sys
import time
import signal
import os
import json
from pathlib import Path
from threading import Thread
import queue

# imports of our modules
from backend import camera_monitor, mic_monitor, process_monitor
from utils.notifier import send_notification

PROJECT_DIR = Path(__file__).parent
STATUS_FILE = PROJECT_DIR / "utils" / "status.json"

def init_status_file():
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATUS_FILE.exists():
        initial = {"camera": {}, "microphone": {}, "processes": {}}
        STATUS_FILE.write_text(json.dumps(initial, indent=2))

def event_watcher(evq):
    """
    Runs in a thread: reads events from the multiprocessing queue and triggers notifications.
    """
    while True:
        try:
            ev = evq.get(timeout=1)
        except Exception:
            continue
        try:
            t = ev.get("type")
            if t == "camera":
                if not ev.get("connected"):
                    send_notification("Camera disconnected", f"Checked at {ev.get('when')}")
                else:
                    send_notification("Camera connected", f"Checked at {ev.get('when')}")
            elif t == "microphone":
                if not ev.get("accessible"):
                    send_notification("Microphone unavailable", f"Checked at {ev.get('when')}")
                else:
                    send_notification("Microphone ready", f"Checked at {ev.get('when')}")
            elif t == "process":
                new = ev.get("new_top", [])
                send_notification("New top process", f"{', '.join(new)}")
            else:
                send_notification("Event", str(ev))
        except Exception as e:
            print("Error in event_watcher:", e)

def start_streamlit():
    """
    Start the Streamlit dashboard as a subprocess using the same Python interpreter
    so it uses the virtualenv packages.
    """
    cmd = [sys.executable, "-m", "streamlit", "run", "ui/dashboard.py", "--server.port", "8501"]
    return subprocess.Popen(cmd, cwd=str(PROJECT_DIR))

def spawn_process(target, args=()):
    p = multiprocessing.Process(target=target, args=args, daemon=True)
    p.start()
    return p

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")  # safer on Windows
    init_status_file()

    # shared queue for events
    event_queue = multiprocessing.Queue()

    # start watchers (as separate processes)
    procs = []
    procs.append(spawn_process(camera_monitor.run, (str(STATUS_FILE), event_queue, 1.0)))
    procs.append(spawn_process(mic_monitor.run, (str(STATUS_FILE), event_queue, 2.0)))
    procs.append(spawn_process(process_monitor.run, (str(STATUS_FILE), event_queue, 5.0)))

    # start event watcher thread (runs in integrator process)
    ev_thread = Thread(target=event_watcher, args=(event_queue,), daemon=True)
    ev_thread.start()

    # start Streamlit UI subprocess
    streamlit_proc = start_streamlit()
    print("Streamlit started at http://localhost:8501")

    try:
        # main loop: keep the parent process alive to manage children
        while True:
            time.sleep(0.5)
            # optional: you can monitor child health here and restart if required
            for p in procs:
                if not p.is_alive():
                    print(f"Child {p.name} died. You could restart it here.")
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # terminate everything
        for p in procs:
            try:
                p.terminate()
            except Exception:
                pass
        try:
            streamlit_proc.terminate()
        except Exception:
            pass
        print("All terminated.")
