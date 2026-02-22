"""
Hello Farm — Daily WhatsApp Reporter

Runs every morning at 7:00 AM and sends each plot's satellite health report
to the farmer's WhatsApp automatically.

Usage:
  python daily_reporter.py            # runs the scheduler (keeps running)
  python daily_reporter.py --now      # send reports immediately (for testing)

Schedule (Windows Task Scheduler):
  Action: python C:\Users\pavan\Hello_Farm\daily_reporter.py --now
  Trigger: Daily at 07:00 AM
  (See README for Task Scheduler setup steps)
"""

import sys
import os
import time
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from src.database import FarmDatabase
from src.weather import WeatherService
from src.satellite import SatelliteMonitor
from src.whatsapp import WhatsAppService
from src.translation import LanguageManager


# ── Helpers ────────────────────────────────────────────────────────────────

def health_emoji(score: int) -> str:
    if score >= 70:
        return "🟢"
    elif score >= 40:
        return "🟡"
    return "🔴"


def health_label(score: int) -> str:
    if score >= 70:
        return "Healthy / ఆరోగ్యంగా ఉంది"
    elif score >= 40:
        return "Moderate / మధ్యస్తంగా ఉంది"
    return "Stress / ఒత్తిడిలో ఉంది"


def irrigation_status(plot: dict) -> str:
    last = plot.get("last_irrigated")
    freq = plot.get("irrigation_frequency_days", 7)
    if not last:
        return f"⚠️ Never watered! / ఎప్పుడూ నీరు పోయలేదు!"
    try:
        days_ago  = (datetime.now() - datetime.fromisoformat(last)).days
        days_left = freq - days_ago
        if days_left <= 0:
            return f"🚨 {abs(days_left)}d overdue! / {abs(days_left)} రోజులు ఆలస్యం!"
        elif days_left <= 2:
            return f"⚠️ Due in {days_left}d / {days_left} రోజుల్లో అవసరం"
        else:
            return f"✅ Due in {days_left}d / {days_left} రోజుల్లో"
    except (ValueError, TypeError):
        return "Unknown / తెలియదు"


def build_report(plot: dict, sat_data: dict, weather: dict) -> str:
    """Build one plot's report block as WhatsApp text."""
    score   = sat_data.get("health_score", 0) or 0
    ndvi    = sat_data.get("ndvi", 0) or 0
    source  = sat_data.get("satellite_source", "Satellite")
    cloud   = sat_data.get("cloud_cover_percent") or sat_data.get("cloud_cover", 0) or 0
    temp    = weather.get("temp_celsius", "N/A")
    hum     = weather.get("humidity_percent", "N/A")
    rain    = weather.get("rainfall_mm", 0) or 0
    cond    = weather.get("conditions", "")

    return (
        f"*{plot['name_english']}* ({plot['name_telugu']})\n"
        f"{health_emoji(score)} Health: {score}/100 — {health_label(score)}\n"
        f"📡 NDVI: {ndvi:.3f} | Source: {source}\n"
        f"☁️ Cloud: {cloud:.0f}%\n"
        f"🌡️ Temp: {temp}°C | 💧 Humidity: {hum}%\n"
        f"🌧️ Rain: {rain}mm | {cond}\n"
        f"💧 Irrigation: {irrigation_status(plot)}"
    )


# ── Main send function ──────────────────────────────────────────────────────

def send_daily_reports(db: FarmDatabase,
                        weather_svc: WeatherService,
                        satellite: SatelliteMonitor,
                        wa: WhatsAppService) -> None:
    """Generate and send the morning report for all plots."""
    plots = db.get_all_plots()
    if not plots:
        print("[Reporter] No plots in database.")
        return

    today     = datetime.now().strftime("%d %b %Y")
    weekday   = datetime.now().strftime("%A")
    due_plots = db.check_irrigation_needed()

    # ── Header ──
    header = (
        f"🌾 *Hello Farm — Morning Report*\n"
        f"📅 {weekday}, {today}\n"
        f"{'─' * 30}"
    )

    # ── One block per plot ──
    blocks = []
    for plot in plots:
        print(f"[Reporter] Processing {plot['name_english']}...")
        try:
            sat_data = satellite.monitor_plot(plot)
        except Exception as e:
            print(f"[Reporter] Satellite error for {plot['name_english']}: {e}")
            sat_data = {"health_score": 0, "ndvi": 0, "satellite_source": "Unavailable"}
        try:
            weather = weather_svc.get_current_weather(
                plot["center_latitude"], plot["center_longitude"]
            )
        except Exception as e:
            print(f"[Reporter] Weather error for {plot['name_english']}: {e}")
            weather = {}
        blocks.append(build_report(plot, sat_data, weather))

    # ── Summary footer ──
    if due_plots:
        overdue_names = ", ".join(d["name"] for d in due_plots)
        footer = (
            f"{'─' * 30}\n"
            f"🚨 *Irrigation needed:* {overdue_names}\n"
            f"నీటిపారుదల అవసరం: {overdue_names}\n\n"
            f"_Hello Farm — AI Crop Monitor_"
        )
    else:
        footer = (
            f"{'─' * 30}\n"
            f"✅ All plots on schedule / అన్ని పొలాలు సరైన స్థితిలో ఉన్నాయి\n\n"
            f"_Hello Farm — AI Crop Monitor_"
        )

    full_message = "\n\n".join([header] + blocks + [footer])

    # ── Send to each plot's WhatsApp number OR the default farmer number ──
    sent_numbers = set()
    for plot in plots:
        wa_number = (plot.get("whatsapp_number") or "").strip()
        if wa_number and wa_number not in sent_numbers:
            print(f"[Reporter] Sending to {wa_number} (plot: {plot['name_english']})")
            wa.send_daily_report(full_message, to_number=wa_number)
            sent_numbers.add(wa_number)

    # Also send to the default farmer number from .env if not already sent
    default_num = os.getenv("FARMER_WHATSAPP", "").strip()
    if default_num and default_num not in sent_numbers:
        print(f"[Reporter] Sending to default farmer number {default_num}")
        wa.send_daily_report(full_message)
        sent_numbers.add(default_num)

    if not sent_numbers:
        print("[Reporter] No WhatsApp numbers configured. Message printed below:")
        print(full_message)

    print(f"[Reporter] Done. Sent to {len(sent_numbers)} number(s).")


# ── Scheduler ───────────────────────────────────────────────────────────────

def run_scheduler(send_hour: int = 7, send_minute: int = 0) -> None:
    """Keep running and send the report every day at send_hour:send_minute."""
    try:
        import schedule
    except ImportError:
        print("Installing 'schedule' package...")
        os.system(f"{sys.executable} -m pip install schedule")
        import schedule

    db         = FarmDatabase()
    db.init_database()
    weather_svc = WeatherService()
    satellite   = SatelliteMonitor()
    wa          = WhatsAppService()

    def job():
        print(f"\n[Reporter] Starting daily reports — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        send_daily_reports(db, weather_svc, satellite, wa)

    time_str = f"{send_hour:02d}:{send_minute:02d}"
    schedule.every().day.at(time_str).do(job)
    print(f"[Reporter] Scheduled daily WhatsApp reports at {time_str}.")
    print("[Reporter] Keep this running in the background. Press Ctrl+C to stop.")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hello Farm Daily WhatsApp Reporter")
    parser.add_argument("--now",   action="store_true", help="Send reports immediately")
    parser.add_argument("--hour",  type=int, default=7,  help="Hour to send daily (24h, default 7)")
    parser.add_argument("--minute",type=int, default=0,  help="Minute to send daily (default 0)")
    args = parser.parse_args()

    if args.now:
        db = FarmDatabase()
        db.init_database()
        print(f"[Reporter] Sending reports now — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        send_daily_reports(db, WeatherService(), SatelliteMonitor(), WhatsAppService())
    else:
        run_scheduler(send_hour=args.hour, send_minute=args.minute)
