from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pytz
import uvicorn
from dotenv import load_dotenv

# Only send updates for this plot for now — others added when ready
ACTIVE_PLOT = "Athota Road Polam"
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from src.database import FarmDatabase
from src.satellite_multi import MultiSatelliteManager
from src.weather import WeatherService
from src.whatsapp import WhatsAppService
from src.telegram_service import TelegramService

print("Initialising Hello Farm Push Server...")

db        = FarmDatabase()
db.init_database()

multi_sat = MultiSatelliteManager()
weather   = WeatherService()
whatsapp  = WhatsAppService()
telegram  = TelegramService()

IST = pytz.timezone("Asia/Kolkata")

# Tracks whether today's morning update was sent (persists across restarts)
_FLAG_FILE = Path(__file__).parent / "data" / ".last_morning_send"


def _mark_morning_sent() -> None:
    _FLAG_FILE.parent.mkdir(exist_ok=True)
    _FLAG_FILE.write_text(datetime.now(IST).strftime("%Y-%m-%d"))


def _morning_sent_today() -> bool:
    if not _FLAG_FILE.exists():
        return False
    return _FLAG_FILE.read_text().strip() == datetime.now(IST).strftime("%Y-%m-%d")

# Recipients — farmer + father + observer (deduped)
_all_recipients = [
    os.getenv("FARMER_WHATSAPP", ""),
    os.getenv("FATHER_WHATSAPP", ""),
    os.getenv("OBSERVER_WHATSAPP", ""),
]
RECIPIENTS: List[str] = list(dict.fromkeys(r.strip() for r in _all_recipients if r.strip()))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ── startup ──
    scheduler.start()
    threading.Thread(target=_startup_catchup, daemon=True).start()
    print("\n" + "=" * 60)
    print("HELLO FARM PUSH SERVER STARTED")
    print("=" * 60)
    print(f"  GEE         : {'connected' if multi_sat.initialized else 'fallback mode'}")
    print(f"  WhatsApp    : {whatsapp.mode}")
    print(f"  Recipients  : {len(RECIPIENTS)} ({', '.join(RECIPIENTS) or 'none'})")
    print(f"  Schedules   :")
    print(f"    - Daily update   : 7:00 AM IST")
    print(f"    - Satellite check : every 6 hours (30d lookback on startup)")
    print(f"    - Weekly summary  : Sundays 8:00 AM IST")
    print(f"  Endpoints   :")
    print(f"    GET /                  health check")
    print(f"    GET /trigger/morning   manual morning send")
    print(f"    GET /trigger/satellite manual satellite check")
    print(f"    GET /trigger/weekly    manual weekly send")
    print("=" * 60 + "\n")

    yield  # server is running

    # ── shutdown ──
    scheduler.shutdown()
    print("Push server stopped")


app = FastAPI(
    title="Hello Farm Push Server",
    description="Automated WhatsApp crop-monitoring notifications",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check() -> Dict:
    return {
        "status":         "ok",
        "service":        "Hello Farm Push Server",
        "gee":            multi_sat.initialized,
        "satellite_mode": "live" if multi_sat.initialized else "demo",
        "whatsapp_mode":  whatsapp.mode,
        "recipients":     len(RECIPIENTS),
        "time_ist":       datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
    }


@app.get("/trigger/morning")
async def trigger_morning() -> Dict:
    send_morning_update()
    return {"status": "triggered", "job": "morning_update"}


@app.get("/trigger/satellite")
async def trigger_satellite() -> Dict:
    check_satellite_updates()
    return {"status": "triggered", "job": "satellite_check"}


@app.get("/trigger/weekly")
async def trigger_weekly() -> Dict:
    send_weekly_summary()
    return {"status": "triggered", "job": "weekly_summary"}


@app.get("/api/ndvi")
async def api_ndvi(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    days: int  = Query(30, description="Lookback days"),
) -> Dict:
    """Public NDVI lookup — returns latest satellite health data for any coordinates."""
    try:
        sat = multi_sat.get_latest_ndvi(
            latitude=lat, longitude=lon, days_lookback=days,
        )
        if not sat:
            return {"status": "no_data", "message": "No satellite imagery found for these coordinates"}

        ndvi = sat["ndvi"]
        health = _ndvi_to_health(ndvi)

        return {
            "status":       "ok",
            "ndvi":         round(ndvi, 4),
            "health_score": health,
            "satellite":    sat.get("satellite", "unknown"),
            "date":         sat.get("date", "unknown"),
            "age_days":     sat.get("age_days", -1),
            "cloud_cover":  round(sat.get("cloud_cover", 0), 1),
            "coordinates":  {"lat": lat, "lon": lon},
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def send_morning_update() -> None:
    print(f"\n{'='*60}")
    print(f"MORNING UPDATE  {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")

    try:
        all_plots = db.get_all_plots()
        plots = [p for p in all_plots if p["name_english"] == ACTIVE_PLOT]
        if not plots:
            print("No plots in database -- skipping")
            return

        te, en = _time_greeting()
        te += "\n\n"
        en += "\n\n"

        # Irrigation check — only for active plot
        due = db.check_irrigation_needed()
        due = [p for p in due if p["name"] == ACTIVE_PLOT]
        if due:
            te += "💧 ఈరోజు నీరు పోయాల్సిన పొలాలు:\n"
            en += "💧 Plots needing water today:\n"
            for p in due:
                te += f"  * {_telugu_name(plots, p['name'])} "
                te += f"({p['days_overdue']}d overdue)\n"
                en += f"  * {p['name']} -- {p['days_overdue']} days overdue\n"
        else:
            te += "✅ పొలం బాగుంది\n"
            en += "✅ Plot is on schedule\n"

        te += "\n"
        en += "\n"

        # Latest satellite NDVI for active plot
        try:
            p0 = plots[0]
            sat = multi_sat.get_latest_ndvi(
                latitude=p0["center_latitude"],
                longitude=p0["center_longitude"],
                days_lookback=30,
            )
            if sat:
                ndvi         = sat["ndvi"]
                health_score = _ndvi_to_health(ndvi)
                history      = db.get_satellite_history(p0["name_english"], days=30)
                trend_te, trend_en, trend_emoji = _compute_trend(ndvi, history)
                advisory_te, advisory_en = _jowar_advisory(ndvi, trend_en, trend_emoji)
                te += (f"🛰️ పొలం ఆరోగ్యం ({sat['satellite']}, {sat['date']}):\n"
                       f"{trend_emoji} NDVI: {ndvi:.3f} | స్కోర్: {health_score}/100 ({trend_te})\n"
                       f"{advisory_te}\n\n")
                en += (f"🛰️ Crop Health ({sat['satellite']}, {sat['date']}):\n"
                       f"{trend_emoji} NDVI: {ndvi:.3f} | Score: {health_score}/100 ({trend_en})\n"
                       f"{advisory_en}\n\n")
            else:
                te += "🛰️ ఉపగ్రహ డేటా అందుబాటులో లేదు\n\n"
                en += "🛰️ No satellite data available\n\n"
        except Exception as exc:
            print(f"  Satellite fetch error: {exc}")

        # Weather for active plot
        try:
            p0 = plots[0]
            w  = weather.get_current_weather(
                p0["center_latitude"], p0["center_longitude"]
            )
            rain = w.get("rainfall_mm", 0) or 0
            te += (f"☀️ వాతావరణం: {w.get('conditions','N/A')}, "
                   f"{w.get('temp_celsius','?')}°C\n")
            en += (f"☀️ Weather: {w.get('conditions','N/A')}, "
                   f"{w.get('temp_celsius','?')}°C\n")
            if rain > 0:
                te += f"🌧️ వర్షం: {rain}mm\n"
                en += f"🌧️ Rainfall: {rain}mm\n"
        except Exception as exc:
            print(f"  Weather fetch error: {exc}")

        message = te + "\n---\n\n" + en
        _broadcast(message)
        _mark_morning_sent()
        print("Morning update sent")

    except Exception as exc:
        print(f"Morning update failed: {exc}")


def check_satellite_updates(days_lookback: int = 7) -> None:
    print(f"\n{'='*60}")
    print(f"SATELLITE CHECK  {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}"
          f"  (lookback={days_lookback}d)")
    print(f"{'='*60}")

    try:
        plots = [p for p in db.get_all_plots()
                 if p["name_english"] == ACTIVE_PLOT]

        for plot in plots:
            print(f"\nChecking {plot['name_english']}...")

            sat = multi_sat.get_latest_ndvi(
                latitude=plot["center_latitude"],
                longitude=plot["center_longitude"],
                days_lookback=days_lookback,
            )

            if not sat:
                print("  No imagery found")
                continue

            already_sent = db.has_sent_notification_for_date(
                plot["id"], sat["date"]
            )
            if already_sent:
                print(f"  Already notified for {sat['date']}")
                continue

            # New data — build and send notification
            print(f"  New data from {sat['satellite']} ({sat['date']})")
            _send_satellite_notification(plot, sat)

    except Exception as exc:
        print(f"Satellite check failed: {exc}")


def _send_satellite_notification(plot: Dict, sat: Dict) -> None:
    try:
        ndvi         = sat["ndvi"]
        health_score = _ndvi_to_health(ndvi)

        # Trend comparison
        history = db.get_satellite_history(plot["name_english"], days=30)
        trend_te, trend_en, trend_emoji = _compute_trend(ndvi, history)

        # LLM-style advisory: current vs ideal Jowar condition
        advisory_te, advisory_en = _jowar_advisory(ndvi, trend_en, trend_emoji)

        # Satellite NDVI heatmap image of the plot
        corners    = plot.get("boundary_coords")   # stored as list or None
        image_path: Optional[str] = None
        try:
            image_path = multi_sat.get_ndvi_image(
                latitude=plot["center_latitude"],
                longitude=plot["center_longitude"],
                corners=corners,
            )
        except Exception as exc:
            print(f"  NDVI image error: {exc}")

        message = (
            f"🛰️ {sat['satellite']} నివేదిక\n\n"
            f"{plot['name_telugu']}:\n"
            f"{trend_emoji} ఆరోగ్యం: {health_score}/100 ({trend_te})\n"
            f"📸 NDVI: {ndvi:.3f}\n"
            f"📅 తేదీ: {sat['date']} ({sat['age_days']} రోజుల క్రితం)\n"
            f"☁️ మేఘాలు: {sat['cloud_cover']:.0f}%\n\n"
            f"{advisory_te}\n\n"
            f"---\n\n"
            f"🛰️ {sat['satellite']} Report\n\n"
            f"{plot['name_english']}:\n"
            f"{trend_emoji} Health: {health_score}/100 ({trend_en})\n"
            f"📸 NDVI: {ndvi:.3f}\n"
            f"📅 Date: {sat['date']} ({sat['age_days']} days ago)\n"
            f"☁️ Clouds: {sat['cloud_cover']:.0f}%\n\n"
            f"{advisory_en}"
        )

        _broadcast(message, image_path)

        # Save reading to satellite_history
        db.save_satellite_reading(
            plot_id=plot["id"],
            date=sat["date"],
            source=sat["satellite"],
            ndvi=ndvi,
            cloud_cover=sat["cloud_cover"],
            health_score=float(health_score),
        )

        # Mark notification as sent (prevents re-sending)
        db.record_satellite_notification(
            plot_id=plot["id"],
            satellite_date=sat["date"],
            satellite_name=sat["satellite"],
            ndvi=ndvi,
        )

        print(f"  Notification sent for {plot['name_english']}")

    except Exception as exc:
        print(f"  Notification send failed: {exc}")


def send_weekly_summary() -> None:
    print(f"\n{'='*60}")
    print(f"WEEKLY SUMMARY  {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print(f"{'='*60}")

    try:
        plots = [p for p in db.get_all_plots()
                 if p["name_english"] == ACTIVE_PLOT]
        if not plots:
            print("No plots -- skipping weekly summary")
            return

        te = "📊 వారపు సారాంశం 📊\n\n"
        en = "📊 Weekly Summary 📊\n\n"

        for plot in plots:
            history = db.get_satellite_history(plot["name_english"], days=7)

            if len(history) >= 2:
                new_ndvi   = history[0].get("ndvi_value", 0.5)
                _, trend_en, emoji = _compute_trend(new_ndvi,
                                                    history[1:])
                te += f"{emoji} {plot['name_telugu']}: {trend_en}\n"
                en += f"{emoji} {plot['name_english']}: {trend_en}\n"
            else:
                te += f"📊 {plot['name_telugu']}: పోలిక లేదు\n"
                en += f"📊 {plot['name_english']}: not enough data yet\n"

        message = te + "\n---\n\n" + en
        _broadcast(message)
        print("Weekly summary sent")

    except Exception as exc:
        print(f"Weekly summary failed: {exc}")


def _broadcast(message: str, image_path: Optional[str] = None) -> None:
    # ── Telegram (primary — no opt-in restrictions) ──────────────────
    if telegram.enabled:
        sent = telegram.broadcast(message, image_path)
        print(f"  Telegram: {sent}/{len(telegram.chat_ids)} delivered")
        return

    # ── Twilio WhatsApp (fallback — kept but inactive when Telegram works) ──
    if not RECIPIENTS:
        print("  No recipients configured — printing to console")
        whatsapp._send_mock("console", message, image_path)
        return

    results = whatsapp.send_to_multiple(message, RECIPIENTS, image_path)
    for r in results:
        print(f"  → {r.get('number','?')}: {r.get('status','?')}")


def _jowar_advisory(
    ndvi: float,
    trend_en: str,
    trend_emoji: str,
) -> tuple:
    """
    Compare current NDVI against ideal Jowar range for the current growth stage.
    Returns (telugu_text, english_text).

    AP Jowar calendar:
      Kharif — sown Jun-Jul, harvest Oct-Nov
      Rabi   — sown Oct-Nov, harvest Mar-Apr
    February = rabi grain-filling stage → ideal NDVI 0.45-0.65
    """
    month = datetime.now(IST).month

    if month in (6, 7):
        stage_en = "germination";             ideal_lo, ideal_hi = 0.15, 0.25
    elif month in (8, 9):
        stage_en = "vegetative growth";       ideal_lo, ideal_hi = 0.35, 0.55
    elif month in (10, 11):
        stage_en = "tillering (rabi sowing)"; ideal_lo, ideal_hi = 0.40, 0.65
    elif month in (12, 1):
        stage_en = "vegetative (rabi)";       ideal_lo, ideal_hi = 0.45, 0.65
    elif month in (2, 3):
        stage_en = "grain filling (rabi)";    ideal_lo, ideal_hi = 0.45, 0.65
    else:  # April-May
        stage_en = "maturity / harvest";      ideal_lo, ideal_hi = 0.25, 0.45

    if ndvi < ideal_lo - 0.05:
        status_en = "Below ideal — crop stress likely"
        status_te = "ఆదర్శ స్థాయి కంటే తక్కువ — పంట ఒత్తిడిలో ఉండవచ్చు"
        action_en = "Check soil moisture now. Irrigate if no rain forecast in 3 days."
        action_te = "వెంటనే నేల తేమ చూడండి. 3 రోజుల్లో వర్షం లేకుంటే నీరు పెట్టండి."
    elif ndvi > ideal_hi + 0.05:
        status_en = "Above ideal — excellent growth"
        status_te = "ఆదర్శ స్థాయి కంటే ఎక్కువ — అద్భుతమైన వృద్ధి"
        action_en = "Crop is thriving. Maintain current schedule. Watch for lodging."
        action_te = "పంట బాగా పెరుగుతోంది. ప్రస్తుత షెడ్యూల్ కొనసాగించండి."
    else:
        status_en = "Within ideal range — healthy"
        status_te = "ఆదర్శ పరిధిలో ఉంది — ఆరోగ్యంగా ఉంది"
        action_en = "Crop is on track. Continue regular irrigation and pest monitoring."
        action_te = "పంట సరిగ్గా ఉంది. సాధారణ నీటిపారుదల మరియు పెస్ట్ పర్యవేక్షణ కొనసాగించండి."

    te = (
        f"🌾 పంట సలహా — {stage_en}\n"
        f"   ఈ దశలో ఆదర్శ NDVI: {ideal_lo:.2f}–{ideal_hi:.2f}\n"
        f"   ప్రస్తుత NDVI: {ndvi:.3f}  {status_te}\n"
        f"   ధోరణి: {trend_emoji} {trend_en}\n"
        f"   ➡ {action_te}"
    )
    en = (
        f"🌾 Crop Advisory — {stage_en.title()}\n"
        f"   Ideal NDVI this stage: {ideal_lo:.2f}–{ideal_hi:.2f}\n"
        f"   Current NDVI: {ndvi:.3f}  {status_en}\n"
        f"   Trend: {trend_emoji} {trend_en.title()}\n"
        f"   ➡ {action_en}"
    )
    return te, en


def _ndvi_to_health(ndvi: float) -> int:
    return min(100, max(0, int((ndvi + 0.2) * 100)))


def _compute_trend(
    current_ndvi: float,
    history: List[Dict],
) -> tuple[str, str, str]:
    if len(history) < 1:
        return "తనిఖీ చేయబడింది", "checked", "📊"

    prev = history[0].get("ndvi_value", current_ndvi)
    delta = current_ndvi - prev

    if delta > 0.05:
        return "మెరుగుపడింది", "improving", "📈"
    elif delta < -0.05:
        return "తగ్గింది",      "declining", "📉"
    else:
        return "స్థిరంగా ఉంది", "stable",    "➡️"


def _time_greeting() -> tuple:
    """Return (telugu_greeting, english_greeting) based on current IST hour."""
    hour = datetime.now(IST).hour
    if 5 <= hour < 12:
        return "శుభోదయం! 🌅", "Good morning! 🌅"
    elif 12 <= hour < 17:
        return "శుభ మధ్యాహ్నం! ☀️", "Good afternoon! ☀️"
    elif 17 <= hour < 21:
        return "శుభ సాయంత్రం! 🌇", "Good evening! 🌇"
    else:
        return "శుభ రాత్రి! 🌙", "Good night! 🌙"


def _telugu_name(plots: List[Dict], english_name: str) -> str:
    for p in plots:
        if p.get("name_english", "") == english_name:
            return p.get("name_telugu", english_name)
    return english_name



scheduler = BackgroundScheduler(timezone=IST)

scheduler.add_job(
    send_morning_update,
    CronTrigger(hour=7, minute=0, timezone=IST),
    id="daily_morning",
    name="Daily 7 AM morning update",
    replace_existing=True,
    misfire_grace_time=3600,   # fire within 1 hour of missed 7 AM
)

scheduler.add_job(
    check_satellite_updates,
    CronTrigger(hour="*/6", timezone=IST),
    id="satellite_check",
    name="Satellite check every 6 hours",
    replace_existing=True,
    misfire_grace_time=3600,   # fire within 1 hour of missed slot
)

scheduler.add_job(
    send_weekly_summary,
    CronTrigger(day_of_week="sun", hour=8, minute=0, timezone=IST),
    id="weekly_summary",
    name="Sunday 8 AM weekly summary",
    replace_existing=True,
    misfire_grace_time=7200,   # fire within 2 hours of missed Sunday 8 AM
)


def _startup_catchup() -> None:
    """
    Runs in a background thread 5 seconds after server starts.

    Two jobs:
    1. If today's morning update was missed (system was off at 7 AM) → send now.
    2. Run a satellite check with 30-day lookback so we always send the latest
       available pass even if the system was offline for a week.
    """
    time.sleep(5)

    if not _morning_sent_today():
        print("[Startup] Morning update not sent today — catching up now...")
        send_morning_update()
    else:
        print("[Startup] Morning update already sent today — no catch-up needed")

    # Always run a satellite check on startup with wide lookback
    # so the latest pass (1–30 days back) is delivered immediately.
    print("[Startup] Running satellite catch-up (30-day lookback)...")
    check_satellite_updates(days_lookback=30)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
