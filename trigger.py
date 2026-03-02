"""
Hello Farm - Job Trigger
Runs a single report job and exits. Called by Windows Task Scheduler.

Usage:
  python trigger.py --morning     # send morning crop report
  python trigger.py --satellite   # check for new satellite data
  python trigger.py --weekly      # send weekly summary
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

LOG_FILE = BASE_DIR / "watchdog.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def log(msg):
    logging.info(msg)
    print(msg)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger.py --morning | --satellite | --weekly")
        sys.exit(1)

    job = sys.argv[1]
    log(f"=== trigger.py {job} started ===")

    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Import server functions (safe - uvicorn only runs under __main__)
        from server import (
            send_morning_update,
            check_satellite_updates,
            send_weekly_summary,
        )

        if job == "--morning":
            log("Running morning update...")
            send_morning_update()
            log("Morning update done.")

        elif job == "--satellite":
            log("Running satellite check...")
            check_satellite_updates(days_lookback=30)
            log("Satellite check done.")

        elif job == "--weekly":
            log("Running weekly summary...")
            send_weekly_summary()
            log("Weekly summary done.")

        else:
            log(f"Unknown job: {job}")
            sys.exit(1)

    except Exception as e:
        log(f"ERROR in trigger.py {job}: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)
