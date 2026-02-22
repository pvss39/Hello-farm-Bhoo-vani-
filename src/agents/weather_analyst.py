"""Weather analyst agent for irrigation timing decisions"""

from typing import Dict, List
from src.llm_manager import create_local_llm
import json
import re


class WeatherAnalystAgent:
    """Specializes in weather patterns and irrigation timing."""
    
    def __init__(self):
        """Initialize weather analysis specialist."""
        self.llm = create_local_llm()
        self.name = "Weather Analyst"
    
    def analyze(
        self, 
        current_weather: Dict, 
        forecast: List[Dict], 
        days_since_irrigation: int
    ) -> Dict:
        """
        Analyze weather for irrigation decisions.
        
        Args:
            current_weather: Dict with temp_celsius, conditions, rainfall_mm_today
            forecast: List of forecast dicts
            days_since_irrigation: Days since last irrigation
            
        Returns:
            {
                "recommendation": "irrigate_now"|"wait_for_rain"|"normal_schedule",
                "reasoning": "one-sentence explanation",
                "confidence": 0.0-1.0
            }
        """
        system_prompt = f"""You are {self.name}, a meteorologist focused on agricultural irrigation.

Your ONLY job: Determine if farmer should irrigate based on weather.

Respond ONLY with valid JSON:
{{
  "recommendation": "irrigate_now"|"wait_for_rain"|"normal_schedule",
  "reasoning": "one-sentence explanation",
  "confidence": 0.0-1.0
}}"""
        
        prompt = f"""Current: {current_weather.get('temp_celsius')}°C, {current_weather.get('conditions')}
Rainfall today: {current_weather.get('rainfall_mm_today', 0)}mm
3-day forecast: {forecast}
Last irrigation: {days_since_irrigation} days ago

Should farmer irrigate today?"""
        
        response = self.llm.query(prompt, system_prompt, temperature=0.1)
        
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"⚠️ Weather agent parsing error: {e}")
        
        return {
            "recommendation": "normal_schedule",
            "reasoning": "Default schedule",
            "confidence": 0.5
        }
