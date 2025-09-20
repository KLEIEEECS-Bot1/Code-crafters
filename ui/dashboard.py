# ui/dashboard.py
import streamlit as st
import json
from pathlib import Path
import time

STATUS_FILE = Path(__file__).parent.parent / "utils" / "status.json"

st.set_page_config(page_title="KeepMePrivate Dashboard", layout="wide")

st.title("KeepMePrivate — Monitoring Dashboard")

col1, col2 = st.columns(2)

def load_status():
    try:
        if STATUS_FILE.exists():
            return json.loads(STATUS_FILE.read_text())
    except Exception:
        return {}
    return {}

with col1:
    st.header("Camera")
    status = load_status().get("camera", {})
    st.write("Connected:", status.get("connected"))
    st.write("Last checked:", status.get("checked_at"))

    if st.button("Refresh camera status"):
        st.rerun()


with col2:
    st.header("Microphone")
    status = load_status().get("microphone", {})
    st.write("Accessible:", status.get("accessible"))
    dev = status.get("device")
    if dev:
        st.write("Device name:", dev.get("name"))
    st.write("Last checked:", status.get("checked_at"))

st.header("Top Processes")
status = load_status().get("processes", {})
st.write("Snapshot time:", status.get("when"))
top = status.get("top", [])
if top:
    st.table(top)
else:
    st.write("No process data yet. Run the monitors.")

st.sidebar.header("Controls")
if st.sidebar.button("Manual refresh page"):
    st.experimental_rerun()

auto_refresh = st.sidebar.checkbox("Auto-refresh every 3s (light demo)")
if auto_refresh:
    # lightweight auto-refresh: re-run page every ~3s (works for demo)
    time.sleep(3)
    st.rerun()


st.markdown("**Notes:** This dashboard reads the shared `utils/status.json` produced by the backend monitors.")
