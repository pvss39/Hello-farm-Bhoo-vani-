"""
Hello Farm - Streamlit Web UI
AI-powered crop monitoring dashboard for Telugu farmers.
"""

import os
import sys

# Fix Windows Unicode encoding for emoji in print() statements
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import streamlit as st
import pydeck as pdk
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import urllib.parse

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# --- GEE credentials from Streamlit Cloud secrets ---
# On Streamlit Cloud, GEE_KEY_JSON secret is written to a temp file
# so gee_provider.py can authenticate exactly as it does locally.
try:
    import tempfile, json
    if hasattr(st, "secrets") and "GEE_KEY_JSON" in st.secrets:
        _key_data = st.secrets["GEE_KEY_JSON"]
        _tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        _tmp.write(_key_data if isinstance(_key_data, str) else json.dumps(dict(_key_data)))
        _tmp.flush()
        os.environ["GEE_KEY_FILE"] = _tmp.name
    if hasattr(st, "secrets") and "GEE_PROJECT" in st.secrets:
        os.environ["GEE_PROJECT"] = st.secrets["GEE_PROJECT"]
except Exception:
    pass

from src.database import FarmDatabase
from src.weather import WeatherService
from src.satellite import SatelliteMonitor
from src.visualization import GraphGenerator
from src.translation import LanguageManager
from src.satellite_manager import SatelliteManager
from src.report_card import ReportCardGenerator

# --- Page Config ---
st.set_page_config(
    page_title="Hello Farm | హెలో ఫార్మ్",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #2e7d32; }
    .sub-header  { font-size: 1rem; color: #666; margin-bottom: 1.5rem; }
    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1b5e20, #2e7d32);
    }
    div[data-testid="stSidebar"] .stMarkdown { color: white; }
    div[data-testid="stSidebar"] label { color: white !important; }
</style>
""", unsafe_allow_html=True)


# --- Initialize Services (cached) ---
@st.cache_resource
def init_database():
    db = FarmDatabase()
    db.init_database()
    # Auto-seed demo plots if database is empty (e.g. on Streamlit Cloud)
    if not db.get_all_plots():
        try:
            from setup_plots import setup_plots
            setup_plots()
        except Exception:
            pass
    return db

@st.cache_resource
def init_weather():
    return WeatherService()

@st.cache_resource
def init_satellite():
    return SatelliteMonitor()

@st.cache_resource
def init_visualizer():
    return GraphGenerator()

@st.cache_resource
def init_translator():
    return LanguageManager()

@st.cache_resource
def init_sat_manager():
    return SatelliteManager()


db             = init_database()
weather_service = init_weather()
satellite      = init_satellite()
visualizer     = init_visualizer()
translator     = init_translator()
sat_manager    = init_sat_manager()


# --- Helpers ---
def get_health_color(score):
    if score < 40:
        return "🔴", "Stress", "#c62828"
    elif score < 70:
        return "🟡", "Moderate", "#f57f17"
    else:
        return "🟢", "Healthy", "#2e7d32"

def get_weather_for_plot(plot):
    return weather_service.get_current_weather(
        plot['center_latitude'], plot['center_longitude']
    )

def get_satellite_for_plot(plot):
    return satellite.monitor_plot(plot)


# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🌾 Hello Farm")
    st.markdown("*హెలో ఫార్మ్*")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Dashboard",
         "📋 Report Card",
         "🛰️ Satellite Schedule",
         "🗺️ Plot Map",
         "➕ Manage Plots",
         "💧 Log Irrigation",
         "📊 Irrigation Status",
         "💬 Chat with Agent",
         "🌍 Try It Yourself"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("**📍 Emani Duggirala, AP**")
    st.markdown("**🌱 Crop:** Jowar (జొన్న)")
    st.markdown("**📱 Language:** EN + TE")
    st.markdown("---")
    st.markdown("**🛰️ Satellite APIs:**")
    for provider, available in sat_manager.available_providers.items():
        status = "✅" if available else "❌"
        st.markdown(f"  {status} {provider.replace('_', ' ').title()}")


# =====================================================
# PAGE: Dashboard
# =====================================================
if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">🌾 Hello Farm Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-powered monitoring for your Jowar plots in Emani Duggirala, AP</p>', unsafe_allow_html=True)

    if satellite.gee.available:
        st.success("🛰️ **Satellite layer: Live** — connected to Google Earth Engine (Sentinel-2 / Landsat).")
    else:
        st.warning("🛰️ **Satellite layer: Demo mode** — using simulated NDVI data. Live GEE integration available when credentials are configured.")

    plots = db.get_all_plots()

    if not plots:
        st.warning("No plots found. Go to **Manage Plots** to add your farm plots, or run `python setup_plots.py`.")
        st.stop()

    due_plots = db.check_irrigation_needed()
    best_sat, _ = sat_manager.select_best_satellite()
    sat_label = best_sat

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Plots", len(plots))
    with col2:
        total_acres = sum(p.get('size_acres', 0) for p in plots)
        st.metric("Total Area", f"{total_acres:.2f} acres")
    with col3:
        st.metric("Plots Need Water", len(due_plots),
                  delta=f"{len(due_plots)} overdue" if due_plots else "All good",
                  delta_color="inverse")
    with col4:
        st.metric("Best Satellite", sat_label)

    st.markdown("---")
    st.subheader("📋 Your Plots")

    for plot in plots:
        sat_data     = get_satellite_for_plot(plot)
        weather_data = get_weather_for_plot(plot)
        health_score = sat_data.get('health_score', 50)
        emoji, status_text, _ = get_health_color(health_score)

        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            with c1:
                st.markdown(f"### {plot['name_english']}")
                st.caption(f"{plot['name_telugu']} | {plot['size_acres']} acres")
                st.caption(f"📍 {plot['center_latitude']:.4f}°N, {plot['center_longitude']:.4f}°E")
            with c2:
                st.metric("Health", f"{health_score}/100")
                st.markdown(f"{emoji} **{status_text}**")
            with c3:
                st.metric("Temperature", f"{weather_data.get('temp_celsius','N/A')}°C")
                st.caption(f"💧 Humidity: {weather_data.get('humidity_percent','N/A')}%")
            with c4:
                last_irrigated = plot.get('last_irrigated')
                if last_irrigated:
                    try:
                        days_ago = (datetime.now() - datetime.fromisoformat(last_irrigated)).days
                        st.metric("Last Watered", f"{days_ago}d ago")
                    except (ValueError, TypeError):
                        st.metric("Last Watered", "Unknown")
                else:
                    st.metric("Last Watered", "Never")
                st.caption(f"Cycle: every {plot.get('irrigation_frequency_days',7)} days")
            st.markdown("---")

    if due_plots:
        st.subheader("⚠️ Irrigation Overdue")
        for dp in due_plots:
            st.error(f"**{dp['name']}** — {dp['days_overdue']} days overdue (last: {dp['last_irrigated']})")


# =====================================================
# PAGE: Report Card
# =====================================================
elif page == "📋 Report Card":
    st.markdown('<p class="main-header">📋 Satellite Report Card</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Day-over-day satellite analysis with comparison graphs</p>', unsafe_allow_html=True)

    plots = db.get_all_plots()
    if not plots:
        st.warning("No plots found. Add plots first.")
        st.stop()

    plot_names = [p['name_english'] for p in plots]
    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected_plot_name = st.selectbox("Select Plot", plot_names)
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        generate = st.button("📋 Generate Report Card", type="primary")

    selected_plot = next((p for p in plots if p['name_english'] == selected_plot_name), None)

    if selected_plot and generate:
        with st.spinner("Analysing satellite data and generating report card..."):
            report_gen = ReportCardGenerator(db)
            card = report_gen.generate_report_card(selected_plot)

        st.markdown("---")
        st.markdown(f"### 📋 Report Card: {card.plot_name}")
        st.caption(f"Date: {card.report_date} | Satellite: {card.satellite_used}")

        m1, m2, m3, m4 = st.columns(4)
        emoji, status_text, _ = get_health_color(card.current_health)
        with m1:
            st.metric("Health Score", f"{card.current_health}/100",
                      delta=f"{card.health_change:+d}" if card.health_change is not None else None)
        with m2:
            st.metric("NDVI", f"{card.current_ndvi:.4f}",
                      delta=f"{card.ndvi_change:+.4f}" if card.ndvi_change is not None else None)
        with m3:
            st.metric("Cloud Cover", f"{card.cloud_cover:.0f}%")
        with m4:
            trend_map = {"improving": "📈 IMPROVING", "declining": "📉 DECLINING",
                         "stable": "➡️ STABLE", "baseline": "📌 BASELINE"}
            st.metric("Trend", trend_map.get(card.trend, card.trend.upper()))

        st.markdown(f"### {emoji} Status: **{status_text}**")

        # Day-over-day comparison
        if not card.is_baseline and card.previous_ndvi is not None:
            st.markdown("---")
            st.subheader("📊 Day-over-Day Comparison")
            prev_col, arrow_col, curr_col = st.columns([2, 1, 2])
            with prev_col:
                st.markdown("**Previous Reading**")
                st.markdown(f"- Date: {card.previous_date}")
                st.markdown(f"- Satellite: {card.previous_satellite}")
                st.markdown(f"- NDVI: {card.previous_ndvi:.4f}")
                pe, ps, _ = get_health_color(card.previous_health or 50)
                st.markdown(f"- Health: {pe} {card.previous_health}/100")
            with arrow_col:
                st.markdown("<br><br>", unsafe_allow_html=True)
                trend_arrows = {"improving": "### 📈\n**IMPROVING**",
                                "declining": "### 📉\n**DECLINING**",
                                "stable":    "### ➡️\n**STABLE**"}
                st.markdown(trend_arrows.get(card.trend, "### ❓"))
            with curr_col:
                st.markdown("**Current Reading**")
                st.markdown(f"- Date: {card.report_date}")
                st.markdown(f"- Satellite: {card.satellite_used}")
                st.markdown(f"- NDVI: {card.current_ndvi:.4f}")
                st.markdown(f"- Health: {emoji} {card.current_health}/100")

            if card.comparison_graph_path and os.path.exists(card.comparison_graph_path):
                st.image(card.comparison_graph_path, use_container_width=True)
        else:
            st.info("This is the **first reading (baseline)**. Generate another report card later to see day-over-day comparison.")

        # Trend graph
        if card.graph_path and os.path.exists(card.graph_path):
            st.markdown("---")
            st.subheader("📈 Health Trend")
            st.image(card.graph_path, use_container_width=True)

        # Recommendation
        st.markdown("---")
        st.subheader("💡 Recommendation")
        st.info(card.recommendation)

        # Weather context
        st.markdown("---")
        st.subheader("☁️ Current Weather")
        weather_data = get_weather_for_plot(selected_plot)
        forecast = weather_service.get_forecast_3day(
            selected_plot['center_latitude'], selected_plot['center_longitude']
        )
        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            st.metric("Temperature", f"{weather_data.get('temp_celsius','N/A')}°C")
        with wc2:
            st.metric("Humidity", f"{weather_data.get('humidity_percent','N/A')}%")
        with wc3:
            st.metric("Conditions", weather_data.get('conditions','Unknown'))

        if forecast:
            st.subheader("📅 3-Day Forecast")
            fcols = st.columns(len(forecast))
            for i, day in enumerate(forecast):
                with fcols[i]:
                    st.markdown(f"**{day.get('date','N/A')}**")
                    st.caption(f"🌡️ {day.get('temp_high','N/A')}°C / {day.get('temp_low','N/A')}°C")
                    st.caption(f"🌧️ Rain: {day.get('rainfall_mm',0)}mm")

        # Telugu summary
        st.markdown("---")
        st.subheader("తెలుగు సారాంశం (Telugu Summary)")
        summary_en = (f"{card.plot_name}: Health {card.current_health}/100. "
                      f"NDVI {card.current_ndvi:.3f}. Trend: {card.trend}. "
                      f"{card.recommendation.split('.')[0]}.")
        summary_te = translator.translate_en_to_te(summary_en)
        st.markdown(f"*{summary_te}*")

        # WhatsApp share
        st.markdown("---")
        st.subheader("📱 Share on WhatsApp")
        wa_msg = (
            f"*Hello Farm Report* - {card.report_date}\n"
            f"Plot: {card.plot_name}\n"
            f"Health: {card.current_health}/100 ({card.trend.upper()})\n"
            f"NDVI: {card.current_ndvi:.3f}\n"
            f"Satellite: {card.satellite_used}\n"
            f"Recommendation: {card.recommendation.split('.')[0]}.\n"
            f"\n{summary_te}"
        )
        wa_encoded = urllib.parse.quote(wa_msg)

        # If plot has a stored WhatsApp number, link directly to that contact
        wa_number = selected_plot.get('whatsapp_number', '').strip().replace('+', '').replace(' ', '')
        if wa_number:
            wa_url = f"https://wa.me/{wa_number}?text={wa_encoded}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:10px 20px;border-radius:6px;font-size:16px;cursor:pointer;">📱 Send to {selected_plot["whatsapp_number"]}</button></a>', unsafe_allow_html=True)
        else:
            wa_url = f"https://wa.me/?text={wa_encoded}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background:#25D366;color:white;border:none;padding:10px 20px;border-radius:6px;font-size:16px;cursor:pointer;">📱 Share via WhatsApp</button></a>', unsafe_allow_html=True)
            st.caption("To send to a specific number, add your WhatsApp number in Manage Plots.")

    # Reading history
    if selected_plot:
        st.markdown("---")
        st.subheader("📜 Reading History")
        try:
            history = db.get_satellite_history(selected_plot_name, days=60)
            if history:
                for rec in history[:10]:
                    ndvi_val   = rec.get('ndvi_value', 0)
                    health_val = int(rec.get('health_score', 50) or 50)
                    source     = rec.get('satellite_source', '?')
                    date_str   = rec.get('check_date', 'Unknown')
                    e, _, _    = get_health_color(health_val)
                    st.markdown(f"  {e} **{date_str}** | NDVI: {ndvi_val:.3f} | Health: {health_val}/100 | {source}")
            else:
                st.caption("No readings yet. Generate your first report card above.")
        except Exception:
            st.caption("No readings yet.")


# =====================================================
# PAGE: Satellite Schedule
# =====================================================
elif page == "🛰️ Satellite Schedule":
    st.markdown('<p class="main-header">🛰️ Satellite Schedule</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Track which satellites pass over your plots and when</p>', unsafe_allow_html=True)

    # Available satellites
    st.subheader("🛰️ Available Satellites")
    for sat in sat_manager.get_available_satellites():
        api_status = "✅ API Key Configured" if sat['api_available'] else "❌ No API Key"
        with st.expander(f"**{sat['name']}** ({sat['operator']}) — {api_status}", expanded=False):
            sc1, sc2, sc3 = st.columns(3)
            with sc1: st.metric("Resolution", f"{sat['resolution_m']}m")
            with sc2: st.metric("Revisit Period", f"{sat['revisit_days']} days")
            with sc3: st.metric("Status", "Active" if sat['api_available'] else "Inactive")
            info = sat_manager.get_satellite_info(sat['name'])
            if info:
                st.markdown(f"**Bands:** {', '.join(info['bands'])}")
                st.markdown(f"**NDVI Bands:** {info['ndvi_bands'][0]} (NIR) / {info['ndvi_bands'][1]} (Red)")
                st.markdown(f"**Swath Width:** {info['swath_km']} km")

    # Best satellite today
    st.markdown("---")
    st.subheader("🎯 Best Satellite Today")
    best_name, best_info = sat_manager.select_best_satellite()
    bc1, bc2 = st.columns(2)
    with bc1:
        st.success(f"**Selected: {best_name}**")
        st.markdown(f"- Reason: {best_info.get('reason', 'Auto-selected')}")
        st.markdown(f"- Pass Date: {best_info.get('pass_date', 'N/A')}")
        st.markdown(f"- Resolution: {best_info.get('resolution_m', 'N/A')}m")
    with bc2:
        if best_info.get('has_api_key', False):
            st.success("API key available — will fetch real satellite data automatically.")
        else:
            st.warning("No API key — using simulated data. Add keys in `.env` file.")

    # 30-day schedule table
    st.markdown("---")
    st.subheader("📅 Satellite Pass Schedule")
    days_ahead = st.slider("Days to show", 7, 60, 30)
    passes = sat_manager.get_pass_schedule(days_ahead)

    if passes:
        rows = []
        for p in passes:
            rows.append({
                "Date":       p.pass_date.strftime("%Y-%m-%d"),
                "Satellite":  p.satellite_name,
                "Resolution": f"{p.resolution_m}m",
                "API Ready":  "✅" if p.has_api_key else "❌",
                "Days Away":  f"+{p.days_until}d",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No passes in this window.")

    # API setup guide
    st.markdown("---")
    st.subheader("🔑 API Key Setup")
    st.markdown("""
Add your satellite API keys to the `.env` file in the project root:

```
# Sentinel Hub (Sentinel-2A/2B) — https://www.sentinel-hub.com/
SENTINEL_CLIENT_ID=your_id_here
SENTINEL_CLIENT_SECRET=your_secret_here

# USGS Earth Explorer (Landsat-8/9) — https://earthexplorer.usgs.gov/
USGS_USERNAME=your_username_here
USGS_PASSWORD=your_password_here
```

The system **automatically selects the best satellite** that has a valid API key.
Multiple keys = better coverage (different satellites pass on different days).
""")


# =====================================================
# PAGE: Plot Map
# =====================================================
elif page == "🗺️ Plot Map":
    st.markdown('<p class="main-header">🗺️ Farm Plot Map</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">All your plots on the map with field boundaries</p>', unsafe_allow_html=True)

    plots = db.get_all_plots()
    if not plots:
        st.warning("No plots found. Go to **Manage Plots** to add your farm plots.")
        st.stop()

    # Build pydeck layers
    # Polygon layer for plots that have corners
    HEALTH_COLORS = {
        "healthy":  [46, 125, 50, 120],   # green
        "moderate": [245, 127, 23, 120],  # amber
        "stress":   [198, 40, 40, 120],   # red
    }
    polygon_data = []
    scatter_data = []
    center_lats, center_lons = [], []

    for plot in plots:
        corners = plot.get('corners', [])
        sat_data     = get_satellite_for_plot(plot)
        health_score = sat_data.get('health_score', 50)
        if health_score >= 70:
            fill = HEALTH_COLORS["healthy"]
        elif health_score >= 40:
            fill = HEALTH_COLORS["moderate"]
        else:
            fill = HEALTH_COLORS["stress"]

        center_lats.append(plot['center_latitude'])
        center_lons.append(plot['center_longitude'])

        if len(corners) >= 3:
            # Close the polygon ring by repeating first corner
            ring = [[c['lon'], c['lat']] for c in corners]
            ring.append(ring[0])
            polygon_data.append({
                "polygon": ring,
                "name": plot['name_english'],
                "health": health_score,
                "fill_color": fill,
            })
        else:
            scatter_data.append({
                "lat": plot['center_latitude'],
                "lon": plot['center_longitude'],
                "name": plot['name_english'],
                "health": health_score,
                "fill_color": fill,
            })

    view_state = pdk.ViewState(
        latitude=sum(center_lats) / len(center_lats),
        longitude=sum(center_lons) / len(center_lons),
        zoom=13,
        pitch=0,
    )

    layers = []
    if polygon_data:
        layers.append(pdk.Layer(
            "PolygonLayer",
            data=polygon_data,
            get_polygon="polygon",
            get_fill_color="fill_color",
            get_line_color=[0, 0, 0, 200],
            line_width_min_pixels=2,
            pickable=True,
            auto_highlight=True,
        ))
    if scatter_data:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=scatter_data,
            get_position=["lon", "lat"],
            get_fill_color="fill_color",
            get_radius=80,
            pickable=True,
        ))

    tooltip = {"html": "<b>{name}</b><br/>Health: {health}/100", "style": {"color": "white"}}
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=view_state,
                             tooltip=tooltip, map_style="mapbox://styles/mapbox/satellite-streets-v11"))

    st.caption("🟢 Healthy  🟡 Moderate  🔴 Stress — click a polygon to see details")

    st.markdown("---")
    st.subheader("📍 Plot Details")
    for plot in plots:
        sat_data     = get_satellite_for_plot(plot)
        health_score = sat_data.get('health_score', 50)
        emoji, status_text, _ = get_health_color(health_score)
        corners = plot.get('corners', [])
        with st.expander(f"{emoji} {plot['name_english']} ({plot['name_telugu']})", expanded=True):
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                st.markdown(f"**Center:** {plot['center_latitude']:.5f}°N, {plot['center_longitude']:.5f}°E")
                st.markdown(f"**Size:** {plot['size_acres']} acres")
                st.markdown(f"**Corners:** {len(corners)} defined")
            with mc2:
                st.markdown(f"**Crop:** {plot.get('crop_type_english','Jowar')} ({plot.get('crop_type_telugu','జొన్న')})")
                st.markdown(f"**Irrigation:** Every {plot.get('irrigation_frequency_days',7)} days")
            with mc3:
                st.markdown(f"**Health:** {emoji} {health_score}/100 ({status_text})")
                st.markdown(f"**NDVI:** {sat_data.get('ndvi',0):.3f}")


# =====================================================
# PAGE: Manage Plots
# =====================================================
elif page == "➕ Manage Plots":
    st.markdown('<p class="main-header">➕ Manage Plots</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Add or remove farm plots — enter all corner GPS coordinates</p>', unsafe_allow_html=True)

    st.subheader("🆕 Add New Plot")

    with st.form("add_plot_form"):
        fc1, fc2 = st.columns(2)
        with fc1:
            name_en = st.text_input("Plot Name (English)*", placeholder="e.g., East Field")
            name_te = st.text_input("Plot Name (Telugu)*",  placeholder="e.g., తూర్పు పొలం")
            crop_en = st.text_input("Crop Type (English)*", value="Jowar")
            crop_te = st.text_input("Crop Type (Telugu)*",  value="జొన్న")
        with fc2:
            size        = st.number_input("Size (acres)*", value=1.0, min_value=0.1, step=0.25)
            freq        = st.number_input("Irrigation Frequency (days)*", value=7, min_value=1, max_value=60)
            whatsapp_no = st.text_input("WhatsApp Number (optional)",
                                        placeholder="+919876543210",
                                        help="Include country code. Alerts sent here.")

        st.markdown("**📍 Plot Corner Coordinates** *(enter all 4 corners of your field)*")
        st.caption("Walk to each corner with your phone → open Google Maps → long-press → copy the lat,lon shown.")

        corner_cols = st.columns(4)
        corners_input = []
        for i, col in enumerate(corner_cols):
            with col:
                st.markdown(f"**Corner {i+1}**")
                clat = st.number_input("Latitude",  key=f"clat_{i}", value=16.3700, format="%.6f")
                clon = st.number_input("Longitude", key=f"clon_{i}", value=80.7200, format="%.6f")
                corners_input.append({"lat": clat, "lon": clon})

        submitted = st.form_submit_button("➕ Add Plot", type="primary")

        if submitted:
            if not name_en.strip() or not name_te.strip():
                st.error("Plot name is required in both English and Telugu.")
            else:
                # Center is auto-computed from corners inside add_plot()
                center_lat = sum(c["lat"] for c in corners_input) / len(corners_input)
                center_lon = sum(c["lon"] for c in corners_input) / len(corners_input)
                try:
                    plot_id = db.add_plot(
                        name_en.strip(), name_te.strip(),
                        crop_en, crop_te,
                        size, center_lat, center_lon, int(freq),
                        corners=corners_input,
                        whatsapp_number=whatsapp_no.strip() or None,
                    )
                    st.success(f"Plot **{name_en}** added with 4 corner coordinates! (ID: {plot_id})")
                    st.markdown(f"*✅ {name_te} పొలం విజయవంతంగా జోడించబడింది*")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding plot: {e}")

    # Existing plots
    st.markdown("---")
    st.subheader("📋 Existing Plots")
    plots = db.get_all_plots()

    if not plots:
        st.info("No plots yet. Add your first plot above.")
    else:
        for plot in plots:
            corners = plot.get('corners', [])
            with st.expander(f"📍 {plot['name_english']} ({plot['name_telugu']})", expanded=False):
                pc1, pc2 = st.columns(2)
                with pc1:
                    st.markdown(f"**Crop:** {plot.get('crop_type_english','')} ({plot.get('crop_type_telugu','')})")
                    st.markdown(f"**Size:** {plot.get('size_acres',0)} acres")
                    st.markdown(f"**Irrigation:** Every {plot.get('irrigation_frequency_days',7)} days")
                    wa = plot.get('whatsapp_number')
                    st.markdown(f"**WhatsApp:** {wa if wa else '—'}")
                with pc2:
                    st.markdown(f"**Center:** {plot['center_latitude']:.5f}°N, {plot['center_longitude']:.5f}°E")
                    readings = db.get_satellite_reading_count(plot['name_english'])
                    st.markdown(f"**Satellite Readings:** {readings}")
                    if corners:
                        st.markdown(f"**Boundary:** {len(corners)} corners defined")
                        for j, c in enumerate(corners):
                            st.caption(f"  Corner {j+1}: {c['lat']:.5f}°N, {c['lon']:.5f}°E")
                    else:
                        st.markdown("**Boundary:** Center point only")
                if st.button(f"🗑️ Delete {plot['name_english']}", key=f"del_{plot['id']}"):
                    if db.delete_plot(plot['name_english']):
                        st.success(f"Plot **{plot['name_english']}** deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete plot.")


# =====================================================
# PAGE: Log Irrigation
# =====================================================
elif page == "💧 Log Irrigation":
    st.markdown('<p class="main-header">💧 Log Irrigation</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Record when you water your plots</p>', unsafe_allow_html=True)

    plots = db.get_all_plots()
    if not plots:
        st.warning("No plots found. Add plots first.")
        st.stop()

    plot_names = [p['name_english'] for p in plots]
    selected_plot_name = st.selectbox("Which plot did you water?", plot_names)
    irrigation_date    = st.date_input("Date", value=datetime.now().date())
    notes              = st.text_input("Notes (optional)", placeholder="e.g., Morning irrigation, used well water")

    if st.button("✅ Log Irrigation", type="primary"):
        try:
            db.log_irrigation(selected_plot_name,
                              date=irrigation_date.isoformat(), notes=notes)
            st.success(f"Irrigation logged for **{selected_plot_name}**!")
            plot_info = db.get_plot_info(selected_plot_name)
            if plot_info:
                freq      = plot_info.get('irrigation_frequency_days', 7)
                next_date = irrigation_date + timedelta(days=freq)
                st.info(f"Next irrigation due: **{next_date.strftime('%Y-%m-%d')}** ({freq} days)")
            st.markdown(f"*✅ {selected_plot_name} కు నీటిపారుదల నమోదు చేయబడింది*")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    st.subheader("📜 Plot Status")
    for plot in plots:
        last = plot.get('last_irrigated')
        freq = plot.get('irrigation_frequency_days', 7)
        if last:
            try:
                days_ago = (datetime.now() - datetime.fromisoformat(last)).days
                next_due = freq - days_ago
                if next_due <= 0:
                    st.warning(f"**{plot['name_english']}** — Last watered {days_ago}d ago. **{abs(next_due)}d overdue!**")
                else:
                    st.success(f"**{plot['name_english']}** — Last watered {days_ago}d ago. Next in {next_due}d.")
            except (ValueError, TypeError):
                st.info(f"**{plot['name_english']}** — Last watered: {last}")
        else:
            st.error(f"**{plot['name_english']}** — Never watered. Irrigation needed!")


# =====================================================
# PAGE: Irrigation Status
# =====================================================
elif page == "📊 Irrigation Status":
    st.markdown('<p class="main-header">📊 Irrigation Status</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Which plots need water and weather-based recommendations</p>', unsafe_allow_html=True)

    plots = db.get_all_plots()
    if not plots:
        st.warning("No plots found. Add plots first.")
        st.stop()

    due_plots = db.check_irrigation_needed()
    if due_plots:
        st.error(f"⚠️ {len(due_plots)} plot(s) need irrigation!")
    else:
        st.success("✅ All plots are up to date with irrigation!")

    st.markdown("---")
    for plot in plots:
        sat_data     = get_satellite_for_plot(plot)
        weather_data = get_weather_for_plot(plot)
        health_score = sat_data.get('health_score', 50)
        emoji, status_text, _ = get_health_color(health_score)
        with st.expander(f"{emoji} {plot['name_english']} ({plot['name_telugu']})", expanded=True):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Plot Info**")
                st.markdown(f"- Crop: {plot.get('crop_type_english','Jowar')} ({plot.get('crop_type_telugu','జొన్న')})")
                st.markdown(f"- Size: {plot.get('size_acres',0)} acres")
                st.markdown(f"- Irrigation Cycle: Every {plot.get('irrigation_frequency_days',7)} days")
                last = plot.get('last_irrigated')
                if last:
                    try:
                        days_ago = (datetime.now() - datetime.fromisoformat(last)).days
                        st.markdown(f"- Last Watered: **{days_ago} days ago**")
                    except (ValueError, TypeError):
                        st.markdown(f"- Last Watered: {last}")
                else:
                    st.markdown("- Last Watered: **Never**")
            with c2:
                st.markdown("**Health & Weather**")
                st.markdown(f"- Health: {emoji} {health_score}/100 ({status_text})")
                st.markdown(f"- NDVI: {sat_data.get('ndvi',0):.3f}")
                st.markdown(f"- Temperature: {weather_data.get('temp_celsius','N/A')}°C")
                st.markdown(f"- Humidity: {weather_data.get('humidity_percent','N/A')}%")
                st.markdown(f"- Rainfall: {weather_data.get('rainfall_mm',0)}mm")
                should, reason = weather_service.should_irrigate_today(plot, weather_data)
                if should:
                    st.success(f"💧 {reason}")
                else:
                    st.info(f"☔ {reason}")

    # Irrigation Calendar
    st.markdown("---")
    st.subheader("📅 Irrigation Calendar")
    plot_names = [p['name_english'] for p in plots]
    cal_plot = st.selectbox("Select plot for calendar", plot_names, key="cal_select")
    if st.button("Generate Calendar"):
        with st.spinner("Creating calendar..."):
            cal_path = visualizer.create_irrigation_calendar(cal_plot)
        if cal_path and os.path.exists(cal_path):
            st.image(cal_path, use_container_width=True)
        else:
            st.warning("Could not generate irrigation calendar.")


# =====================================================
# PAGE: Chat with Agent
# =====================================================
elif page == "💬 Chat with Agent":
    st.markdown('<p class="main-header">💬 Chat with Farm Agent</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Talk to your AI farming assistant in English or Telugu</p>', unsafe_allow_html=True)

    @st.cache_resource
    def init_agent():
        from src.agent import FarmAgent
        # Ollama only works locally — disable on Streamlit Cloud
        use_ollama = not (hasattr(st, "secrets") and len(st.secrets) > 0)
        return FarmAgent(database=db, weather_service=weather_service,
                         satellite_monitor=satellite, use_ollama=use_ollama)

    agent = init_agent()

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": (
                "🌾 Hello! I'm your farm AI assistant.\n\n"
                "You can ask me things like:\n"
                "- *I watered thurpu polam*\n"
                "- *Show athota status*\n"
                "- *Which plots need water?*\n"
                "- *Munnagi satellite report*\n"
                "- *help*\n\n"
                "నమస్కారం! నేను మీ వ్యవసాయ AI సహాయకుడిని."
            )}
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Type your message... / మీ సందేశాన్ని టైప్ చేయండి..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = agent.process_message(prompt)
                except Exception as e:
                    response = f"Sorry, I encountered an error: {e}"
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


# =====================================================
# PAGE: Try It Yourself
# =====================================================
elif page == "🌍 Try It Yourself":
    st.markdown('<p class="main-header">🌍 Try It Yourself</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Run a live satellite + weather analysis on any location — no account needed</p>', unsafe_allow_html=True)

    # GEE mode banner
    if satellite.gee.available:
        st.success("🛰️ **Live Mode** — real Sentinel-2 / Landsat NDVI via Google Earth Engine.")
    else:
        st.info("🛰️ **Demo Mode** — simulated NDVI (realistic seasonal values). Live GEE available when credentials are configured.")

    st.markdown("---")

    # --- Location presets ---
    PRESETS = {
        "📍 Emani Duggirala, AP (Farmer's plots)": {"lat": 16.3700, "lon": 80.7200, "label": "Jowar farm, Andhra Pradesh, India"},
        "🌾 Bellary, Karnataka (Jowar belt)":       {"lat": 15.1394, "lon": 76.9214, "label": "Jowar growing region, Karnataka"},
        "🌽 Kansas, USA (Wheat belt)":               {"lat": 38.7000, "lon": -98.0000, "label": "Great Plains wheat, Kansas USA"},
        "🌿 Custom location":                        None,
    }

    col_preset, col_view = st.columns([3, 1])
    with col_preset:
        preset_choice = st.selectbox("Choose a location preset", list(PRESETS.keys()))
    with col_view:
        st.markdown("<br>", unsafe_allow_html=True)
        view_mode = st.radio("View", ["English", "తెలుగు"], horizontal=True, key="try_view")

    preset_val = PRESETS[preset_choice]

    if preset_val is None:
        # Custom lat/lon
        c1, c2 = st.columns(2)
        with c1:
            custom_lat = st.number_input("Latitude", value=16.3700, format="%.6f", min_value=-90.0, max_value=90.0)
        with c2:
            custom_lon = st.number_input("Longitude", value=80.7200, format="%.6f", min_value=-180.0, max_value=180.0)
        analysis_lat   = custom_lat
        analysis_lon   = custom_lon
        location_label = f"Custom ({custom_lat:.4f}°, {custom_lon:.4f}°)"
    else:
        analysis_lat   = preset_val["lat"]
        analysis_lon   = preset_val["lon"]
        location_label = preset_val["label"]
        st.caption(f"📍 {location_label}  |  {analysis_lat:.4f}°N, {analysis_lon:.4f}°E")

    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    # --- Session history init ---
    if "try_history" not in st.session_state:
        st.session_state.try_history = []

    # --- Run analysis ---
    if run_btn:
        with st.spinner("Fetching satellite + weather data..."):
            try:
                sat_result = satellite.monitor_plot({
                    "center_latitude":  analysis_lat,
                    "center_longitude": analysis_lon,
                    "name_english":     location_label,
                })
            except Exception as e:
                sat_result = {"ndvi": 0.35, "health_score": 50, "satellite_name": "Demo", "source": "error"}
                st.warning(f"Satellite fetch note: {e}")

            try:
                wx_result = weather_service.get_current_weather(analysis_lat, analysis_lon)
            except Exception as e:
                wx_result = {}
                st.warning(f"Weather fetch note: {e}")

        ndvi         = sat_result.get("ndvi", 0)
        health       = int(sat_result.get("health_score", 0) or 0)
        sat_name     = sat_result.get("satellite_name", sat_result.get("satellite", "Unknown"))
        sat_source   = sat_result.get("source", "")
        emoji, status_text, _ = get_health_color(health)

        temp      = wx_result.get("temp_celsius", "N/A")
        humidity  = wx_result.get("humidity_percent", "N/A")
        rainfall  = wx_result.get("rainfall_mm", 0)
        conditions = wx_result.get("conditions", "N/A")

        # Save to session history
        st.session_state.try_history.insert(0, {
            "time":     datetime.now().strftime("%H:%M:%S"),
            "location": location_label,
            "lat":      analysis_lat,
            "lon":      analysis_lon,
            "ndvi":     ndvi,
            "health":   health,
            "status":   status_text,
            "temp":     temp,
            "sat":      sat_name,
        })
        # Keep last 10
        st.session_state.try_history = st.session_state.try_history[:10]

        st.markdown("---")
        st.subheader(f"Results: {location_label}")

        # NDVI health bar
        bar_color = "#2e7d32" if health >= 70 else ("#f57f17" if health >= 40 else "#c62828")
        st.markdown(f"""
<div style="background:#eee;border-radius:8px;height:24px;width:100%;margin-bottom:8px;">
  <div style="background:{bar_color};width:{health}%;height:100%;border-radius:8px;
              display:flex;align-items:center;padding-left:10px;color:white;font-weight:bold;font-size:14px;">
    {health}/100
  </div>
</div>
""", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric("Health Score", f"{health}/100")
        with m2: st.metric("NDVI", f"{ndvi:.3f}")
        with m3: st.metric("Temperature", f"{temp}°C")
        with m4: st.metric("Humidity", f"{humidity}%")

        st.markdown("---")

        if view_mode == "English":
            st.subheader("📊 Technical Analysis")
            st.markdown(f"""
| Field | Value |
|---|---|
| **Location** | {location_label} |
| **Coordinates** | {analysis_lat:.4f}°N, {analysis_lon:.4f}°E |
| **Satellite** | {sat_name} ({sat_source}) |
| **NDVI** | {ndvi:.4f} |
| **Health Score** | {emoji} {health}/100 — {status_text} |
| **Temperature** | {temp}°C |
| **Humidity** | {humidity}% |
| **Rainfall** | {rainfall} mm |
| **Conditions** | {conditions} |
""")
            # Interpretation
            if health >= 70:
                interpretation = f"Vegetation is **healthy** with NDVI of {ndvi:.3f}. The crop canopy is dense and photosynthetically active."
            elif health >= 40:
                interpretation = f"Vegetation shows **moderate stress** (NDVI {ndvi:.3f}). Consider irrigation or soil nutrient assessment."
            else:
                interpretation = f"Vegetation under **significant stress** (NDVI {ndvi:.3f}). Immediate intervention may be needed."
            st.info(f"**Interpretation:** {interpretation}")

        else:  # Telugu view
            st.subheader("🌾 రైతు నివేదిక (Farmer Report)")

            if health >= 70:
                te_status   = "మొక్కలు ఆరోగ్యంగా ఉన్నాయి"
                te_advice   = "మీ పంట బాగా పెరుగుతోంది. ప్రస్తుతం ఎరువులు లేదా నీటిపారుదల అవసరం లేదు."
            elif health >= 40:
                te_status   = "మొక్కలకు కొంచెం ఒత్తిడి ఉంది"
                te_advice   = "నీటిపారుదల మరియు పోషకాల స్థాయిని తనిఖీ చేయండి."
            else:
                te_status   = "మొక్కలకు తీవ్రమైన ఒత్తిడి ఉంది"
                te_advice   = "వెంటనే నీరు పెట్టండి మరియు నిపుణులను సంప్రదించండి."

            st.markdown(f"""
| వివరాలు | విలువ |
|---|---|
| **స్థలం** | {location_label} |
| **ఉపగ్రహం** | {sat_name} |
| **NDVI విలువ** | {ndvi:.3f} |
| **పంట ఆరోగ్యం** | {emoji} {health}/100 |
| **ఉష్ణోగ్రత** | {temp}°C |
| **తేమ** | {humidity}% |
| **వర్షం** | {rainfall} మి.మీ. |
""")
            st.success(f"**{te_status}**")
            st.info(f"**సలహా:** {te_advice}")

    # --- Session history table ---
    if st.session_state.try_history:
        st.markdown("---")
        st.subheader("🕓 This Session — Analysis History")
        history_rows = []
        for h in st.session_state.try_history:
            e, s, _ = get_health_color(h["health"])
            history_rows.append({
                "Time":     h["time"],
                "Location": h["location"],
                "NDVI":     f"{h['ndvi']:.3f}",
                "Health":   f"{e} {h['health']}/100",
                "Status":   h["status"],
                "Temp":     f"{h['temp']}°C",
                "Satellite": h["sat"],
            })
        st.dataframe(history_rows, use_container_width=True, hide_index=True)
        if st.button("🗑️ Clear History"):
            st.session_state.try_history = []
            st.rerun()
