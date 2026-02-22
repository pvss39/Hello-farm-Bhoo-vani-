"""
Satellite analyzer test

Tests WOW-3: Intelligent NDVI interpretation with agronomist expertise.
"""

from src.satellite_analyzer import SatelliteAnalyzer

print("🔧 Testing WOW-3: Satellite Intelligence\n")
print("=" * 70)

# Initialize analyzer
analyzer = SatelliteAnalyzer(use_cloud=False)

# Test data
test_plots = [
    {
        "plot_name": "Thurpu Polam",
        "current_ndvi": 0.65,
        "historical_ndvi": [0.60, 0.62, 0.64, 0.65],
        "weather_data": {"temp_celsius": 32, "rainfall_mm_today": 0},
        "days_since_irrigation": 5
    },
    {
        "plot_name": "Athota Road Polam",
        "current_ndvi": 0.35,
        "historical_ndvi": [0.40, 0.38, 0.36, 0.35],
        "weather_data": {"temp_celsius": 34, "rainfall_mm_today": 2},
        "days_since_irrigation": 8
    },
    {
        "plot_name": "Munnagi Road Polam",
        "current_ndvi": 0.72,
        "historical_ndvi": [0.68, 0.70, 0.71, 0.72],
        "weather_data": {"temp_celsius": 30, "rainfall_mm_today": 5},
        "days_since_irrigation": 3
    }
]

print("\n📊 Analyzing satellite data for all plots...\n")

for plot in test_plots:
    print(f"\n🌾 Analyzing: {plot['plot_name']}")
    print(f"   NDVI: {plot['current_ndvi']}")
    
    result = analyzer.analyze_health(
        plot_name=plot["plot_name"],
        current_ndvi=plot["current_ndvi"],
        historical_ndvi=plot["historical_ndvi"],
        weather_data=plot["weather_data"],
        days_since_irrigation=plot["days_since_irrigation"]
    )
    
    print(f"\n   Assessment: {result['health_assessment']}")
    print(f"   Concerns: {result['concerns']}")
    print(f"   Confidence: {result['confidence']:.2%}")

print("\n" + "=" * 70)
print("✅ WOW-3 Satellite Intelligence Test Complete!")
