"""
Hello Farm — Pitch Co-Pilot
Run alongside the main demo. Type any question the panel asks → get instant answer.
Access from phone: http://<your-laptop-ip>:8502
"""

import streamlit as st
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Hello Farm — Pitch Co-Pilot",
    page_icon="🌾",
    layout="centered",
)

# ── Full project knowledge base ─────────────────────────────────────────────

PROJECT_CONTEXT = """
You are the pitch co-pilot for "Hello Farm" — an AI-powered crop monitoring system
built for Telugu farmers in Andhra Pradesh, India. Answer any question the panel asks
during a startup pitch. Be concise, confident, and use real numbers where available.
If asked something speculative, give the honest plan. Never make up false data.

=== HELLO FARM — COMPLETE PROJECT KNOWLEDGE ===

WHAT IT IS:
Hello Farm is an AI crop monitoring system that gives small-scale farmers in Andhra Pradesh
daily crop health reports, satellite NDVI analysis, weather alerts, and irrigation reminders
— all delivered automatically to their phone via Telegram in Telugu and English.
No app download needed. Works on any phone with Telegram.

THE FARMER (Real User):
- 3 Jowar (Sorghum) plots in Emani Duggirala Mandal, Krishna District, Andhra Pradesh
- Plots: Thurpu Polam, Athota Road Polam, Munnagi Road Polam
- Coordinates: ~16.37°N, 80.72°E
- Current crop: Rabi Jowar (sown Oct-Nov, harvest Mar-Apr)
- Currently in grain-filling stage (Feb-Mar) — ideal NDVI: 0.45–0.65

PROBLEM BEING SOLVED:
- 140 million small farmers in India own less than 2 hectares
- They make irrigation and pesticide decisions by eye — no data
- Satellite tools like Sentinel Hub cost ₹50,000+/year for professional access
- Weather stations at farm level don't exist for most villages
- Crop loss from wrong irrigation timing: 20-30% yield reduction
- Government extension services reach only 6% of farmers (ICAR data)

OUR SOLUTION — WHAT IT DOES TODAY (LIVE):
1. Daily 7 AM Telegram message: crop health score, NDVI value, weather, irrigation status
2. Satellite NDVI from Sentinel-2A/2B (10m resolution, 5-day revisit) via Google Earth Engine
3. Weather from OpenWeather API (real-time temperature, humidity, rainfall)
4. Irrigation alerts: tracks last watered date, flags overdue plots
5. Crop advisory in Telugu + English based on current growth stage
6. Weekly summary every Sunday 8 AM
7. New satellite pass detected → instant Telegram notification with NDVI heatmap image
8. AI agent (LangGraph) answers farmer questions in Telugu

TECH STACK:
- Frontend: Streamlit (Python) — 8 pages dashboard
- Backend: FastAPI + APScheduler (server.py) — scheduled reports
- Satellite: Google Earth Engine + Sentinel Hub + Landsat fallback
- Weather: OpenWeather API
- Notifications: Telegram Bot API
- Database: SQLite (plots, irrigation_log, satellite_history)
- AI Agent: LangGraph workflow with Claude/local LLM
- Runs on: Windows PC, always-on, auto-starts via Windows Task Scheduler
- Languages: Telugu + English throughout

TRACTION / PROOF:
- Fully working system deployed on real farmer's plots today
- Daily Telegram messages going to farmer's phone and father's phone
- Satellite data flowing from Google Earth Engine (GEE connected)
- System auto-restarts via watchdog — zero manual intervention needed
- Real NDVI readings tracked and stored with trend analysis

MARKET SIZE:
- India: 140 million farming households
- Andhra Pradesh alone: 6.2 million farming households
- Krishna District (our target): 420,000 farming families
- Average farm size in AP: 1.1 hectares
- Current crop monitoring market India: $180M (2024), growing 18% YoY
- Precision agriculture India market: projected $3.2B by 2028 (MarketsandMarkets)

REVENUE MODEL (PLANNED):
- Freemium: basic daily report free (Telegram)
- Premium ₹199/month: NDVI heatmap images, pest alerts, market price integration
- B2B: FPOs (Farmer Producer Organisations) — bulk subscription ₹50/farmer/month
- Government: AP Agriculture Dept, PM-KISAN integration potential
- Target: 10,000 farmers in Year 1 at ₹99/month avg = ₹1.19 Cr ARR

COST SAVINGS FOR A FARMER:
- Right irrigation timing: saves 2-3 irrigations/season = ₹3,000-5,000/acre
- Early stress detection: prevents 15-20% yield loss = ₹8,000-12,000/acre
- Average Jowar yield value in AP: ₹35,000-45,000/acre
- ROI for farmer at ₹199/month: 40x return on investment

COMPETITION:
- CropIn: targets large farms and agribusinesses, not small farmers
- DeHaat: input supply focused, not monitoring
- Fasal: soil sensor hardware required (expensive, ₹15,000 setup)
- Plantix: disease detection only, no satellite, no Telugu
- Hello Farm advantage: zero hardware, works on basic smartphone, Telugu-native,
  satellite + weather + AI combined, auto-daily delivery via Telegram

OPERATION TERRASYNC (PHASE 2 ROADMAP):
- Drone integration: real-time NDVI from drone flights (no cloud cover problem)
- Multispectral camera on drone: cm-level resolution vs Sentinel's 10m
- Real-time data pipeline: drone flies → images processed → NDVI map in 30 min
- Multimodal AI model: combines drone imagery + weather + soil + crop history
- Timeline: Season data collection 2026 Kharif → model training → deploy Rabi 2026
- Hardware partner discussions: exploring tie-ups with drone rental services in AP

WHY NOW:
- GEE (Google Earth Engine) opened free access for small research projects in 2023
- Telegram penetration in AP rural areas: 67% smartphone users have Telegram
- PM-KISAN digital push: farmers already comfortable with phone-based govt services
- Sentinel-2C launched 2024 — 5-day revisit now more reliable

THE TEAM (current):
- Solo founder/developer — built entire stack
- Real farmer as first user (family farm)
- Advisor: exploring partnerships with ICAR-CRIDA Hyderabad

ASK (what we want from the panel):
- Mentorship: connections to AP Agriculture Dept for pilot program
- Funding: ₹15 lakh seed to onboard 500 farmers in Krishna District in 6 months
- Network: FPO connections for B2B channel

COMMON TOUGH QUESTIONS:
Q: What if the satellite has cloud cover?
A: We use multi-satellite fallback: Sentinel-2 + Landsat-8/9. If both are blocked,
   we use the last clean pass with a timestamp so the farmer knows the data age.
   For Phase 2, drone eliminates this entirely.

Q: How is this different from the government's mFarmer or IFFCO Kisan app?
A: Those are advisory platforms — they push generic content. Hello Farm monitors
   THIS farmer's specific plot via satellite and sends personalized data. It's
   the difference between a weather forecast and a weather station on your farm.

Q: What's the accuracy of NDVI-based health scores?
A: Sentinel-2 NDVI has 85-90% correlation with actual crop stress in peer-reviewed
   studies for Sorghum crops in semi-arid India (ICRISAT, 2022).
   Our advisory thresholds are calibrated for Jowar growth stages in AP's climate.

Q: Can it scale beyond 3 plots?
A: Yes — the system is plot-agnostic. Adding a new farmer takes 2 minutes (GPS
   coordinates + phone number). No hardware, no site visit.

Q: What happens if the farmer doesn't have internet?
A: Telegram messages are delivered when they come online. The daily report is
   queued. The monitoring still runs on our server continuously.

Q: Why Telegram and not WhatsApp?
A: WhatsApp Business API requires Meta approval and costs ₹0.80/message.
   Telegram Bot API is free, no message limits, no opt-in restrictions,
   and has equal penetration in rural AP.

Q: Is the data private?
A: Plot coordinates and farm data stored locally on our server (SQLite).
   No data sold to third parties. Farmer owns their data.
"""

# ── UI ───────────────────────────────────────────────────────────────────────

st.markdown("## 🌾 Hello Farm — Pitch Co-Pilot")
st.markdown("*Type any question the panel asks. Get instant answer.*")
st.divider()

# Quick reference chips
st.markdown("**Quick answers:**")
col1, col2, col3, col4 = st.columns(4)
quick = {
    "Market size": "What is the market size for Hello Farm?",
    "Revenue model": "What is the revenue model?",
    "vs Competition": "How is Hello Farm different from competitors?",
    "TerraSync": "What is Operation TerraSync?",
    "Accuracy": "What is the accuracy of your NDVI data?",
    "Cost saving": "How much money does a farmer save?",
    "Scale": "Can this scale beyond 3 plots?",
    "Ask": "What are you asking from the panel?",
}

cols = [col1, col2, col3, col4]
for i, (label, question) in enumerate(quick.items()):
    if cols[i % 4].button(label, use_container_width=True):
        st.session_state["prefill"] = question

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input
prefill = st.session_state.pop("prefill", "") if "prefill" in st.session_state else ""
question = st.chat_input("Type the panel's question here...")

if not question and prefill:
    question = prefill

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(""):
            try:
                api_key = os.getenv("ANTHROPIC_API_KEY", "")
                if not api_key:
                    st.error("Add ANTHROPIC_API_KEY to your .env file")
                    st.stop()

                client = anthropic.Anthropic(api_key=api_key)
                response = client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=400,
                    system=PROJECT_CONTEXT,
                    messages=[
                        {"role": "user", "content": question}
                    ],
                )
                answer = response.content[0].text
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Error: {e}")

# Clear button
if st.session_state.messages:
    if st.button("Clear chat", type="secondary"):
        st.session_state.messages = []
        st.rerun()

st.divider()
st.caption("Running on port 8502 · Open on phone: http://YOUR-PC-IP:8502")
