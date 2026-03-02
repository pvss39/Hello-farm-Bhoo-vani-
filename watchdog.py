"""
Hello Farm - Auto Watchdog
Keeps Streamlit server running whenever system is on and internet is available.
On wake from sleep: sends all missed reports immediately via Telegram.
"""

import subprocess
import time
import socket
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = r"c:\Users\pavan\Hello_Farm"
LOG_FILE = os.path.join(BASE_DIR, "watchdog.log")
STREAMLIT_EXE = os.path.join(BASE_DIR, ".venv", "Scripts", "streamlit.exe")
PYTHON_EXE = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")
TRIGGER_PY = os.path.join(BASE_DIR, "trigger.py")
APP_PY = os.path.join(BASE_DIR, "app.py")
SERVER_PY = os.path.join(BASE_DIR, "server.py")
MORNING_FLAG = Path(BASE_DIR) / "data" / ".last_morning_send"
CHECK_INTERVAL = 30  # seconds between checks

sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def log(msg):
    logging.info(msg)

# Load Telegram service
try:
    from src.telegram_service import TelegramService
    _tg = TelegramService()
except Exception as e:
    _tg = None
    log(f"Telegram init failed: {e}")

def notify(text):
    log(f"NOTIFY: {text}")
    if _tg and _tg.enabled:
        try:
            _tg.broadcast(text)
        except Exception as e:
            log(f"Telegram send error: {e}")

def has_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=5)
        return True
    except OSError:
        return False

def _port_in_use(port: int) -> bool:
    try:
        import socket as _s
        with _s.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False

def is_streamlit_running():
    return _port_in_use(8501)

def is_server_running():
    return _port_in_use(8000)

def start_streamlit():
    log("Starting Streamlit...")
    subprocess.Popen(
        [STREAMLIT_EXE, "run", APP_PY,
         "--server.headless", "true",
         "--server.port", "8501"],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def start_server():
    log("Starting crop server (server.py)...")
    subprocess.Popen(
        [PYTHON_EXE, SERVER_PY],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def morning_sent_today() -> bool:
    try:
        if not MORNING_FLAG.exists():
            return False
        return MORNING_FLAG.read_text().strip() == datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return False

def run_trigger(job: str):
    """Run trigger.py job in background (non-blocking)."""
    log(f"Running catch-up: {job}")
    subprocess.Popen(
        [PYTHON_EXE, TRIGGER_PY, job],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def catchup_missed_reports():
    """After wake from sleep — send everything that was missed."""
    now = datetime.now()
    missed = []

    # Morning report — if past 7 AM and not sent yet today
    if now.hour >= 7 and not morning_sent_today():
        missed.append("morning report")
        run_trigger("--morning")
        time.sleep(3)

    # Always run satellite check on wake — catches any new pass
    missed.append("satellite check")
    run_trigger("--satellite")

    if missed:
        log(f"Wake catch-up: running {', '.join(missed)}")
    else:
        log("Wake catch-up: morning already sent, satellite check queued")

def main():
    log("=== Hello Farm Watchdog started ===")

    was_online = False
    ui_notified = False
    crop_notified = False
    first_run = True

    while True:
        online = has_internet()
        ui_up = is_streamlit_running()
        crop_up = is_server_running()

        if online and not was_online:
            if first_run:
                log("Internet connected (startup)")
                first_run = False
            else:
                log("Internet reconnected — PC woke from sleep. Waiting 20s...")
                time.sleep(20)  # let Windows fully reconnect
                log("Running catch-up for missed reports...")
                catchup_missed_reports()

            was_online = True
            ui_notified = False
            crop_notified = False

        if not online and was_online:
            log("Internet lost (sleep or disconnect)")
            was_online = False
            ui_notified = False
            crop_notified = False
            first_run = False

        # ── Streamlit UI (port 8501) ──
        if online and not ui_up:
            log("Streamlit not running - starting...")
            ui_notified = False
            start_streamlit()
            time.sleep(6)
            if is_streamlit_running():
                log("Streamlit started OK")
                ui_notified = True
            else:
                log("ERROR: Streamlit failed to start")
        elif ui_up and not ui_notified:
            log("Streamlit running")
            ui_notified = True

        # ── Crop server (port 8000) ──
        if online and not crop_up:
            log("Crop server not running - starting...")
            crop_notified = False
            start_server()
            time.sleep(20)  # GEE init takes ~15s
            if is_server_running():
                log("Crop server started OK")
                crop_notified = True
            else:
                log("ERROR: Crop server failed to start")
                notify("Hello Farm ERROR: Crop server failed to start!")
        elif crop_up and not crop_notified:
            log("Crop server running")
            crop_notified = True

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
