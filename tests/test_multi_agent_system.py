"""
Multi-agent system orchestration test

Tests WOW-4: Coordinated workflow of 4 specialized agents.
"""

from src.multi_agent_system import AgentCoordinator

print("🚀 Testing Multi-Agent System...\n")

# Initialize coordinator
coordinator = AgentCoordinator()

# Test data
plot_data = {
    "plot_id": "P001",
    "name": "Thurpu Polam",
    "crop_type_english": "Jowar"
}

satellite_data = {
    "ndvi": 0.62,
    "cloud_cover": 15
}

weather_data = {
    "temp_celsius": 32,
    "conditions": "Clear",
    "rainfall_mm_today": 0
}

forecast = [
    {"day": "Tomorrow", "temp": 33, "conditions": "Clear"},
    {"day": "+2 days", "temp": 32, "conditions": "Clear"}
]

historical_ndvi = [0.58, 0.60, 0.61, 0.62]

# Run comprehensive analysis
result = coordinator.analyze_plot_comprehensive(
    plot_data=plot_data,
    satellite_data=satellite_data,
    weather_data=weather_data,
    forecast_data=forecast,
    historical_ndvi=historical_ndvi,
    days_since_irrigation=3,
    farmer_language="telugu"
)

# Display results
print("📊 ANALYSIS RESULTS:\n")
print(result["technical_report"])
print("\n🗣️ FARMER MESSAGE (Telugu):")
print(result["farmer_message"])
print("\n✅ WOW-4 Code Creation Complete")
