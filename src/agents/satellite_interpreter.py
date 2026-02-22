"""Satellite interpreter agent for NDVI and remote sensing analysis"""

from typing import Dict, List
from src.llm_manager import create_local_llm
import json
import re


class SatelliteInterpreterAgent:
    """Specializes in interpreting satellite imagery and NDVI data."""
    
    def __init__(self):
        """Initialize satellite interpretation specialist."""
        self.llm = create_local_llm()
        self.name = "Satellite Interpreter"
    
    def analyze(self, ndvi: float, cloud_cover: int, historical_data: List[float]) -> Dict:
        """
        Interpret satellite data and NDVI values.
        
        Args:
            ndvi: Current NDVI value (0.0-1.0)
            cloud_cover: Cloud coverage percentage
            historical_data: List of recent NDVI values
            
        Returns:
            {
                "interpretation": "one-sentence finding",
                "severity": "normal"|"warning"|"critical",
                "confidence": 0.0-1.0
            }
        """
        system_prompt = f"""You are {self.name}, an expert in remote sensing for agriculture.

Your ONLY job: Interpret NDVI satellite data for crop health.

NDVI ranges:
- 0.0-0.2: Bare soil/severe stress
- 0.2-0.4: Moderate stress
- 0.4-0.6: Moderate health
- 0.6-0.8: Healthy
- 0.8+: Very healthy

Respond ONLY with valid JSON:
{{
  "interpretation": "one-sentence finding",
  "severity": "normal"|"warning"|"critical",
  "confidence": 0.0-1.0
}}"""
        
        prompt = f"""NDVI: {ndvi:.3f}
Cloud cover: {cloud_cover}%
7-day history: {[round(x, 3) for x in historical_data[-7:]]}

What does this satellite data tell us?"""
        
        response = self.llm.query(prompt, system_prompt, temperature=0.1)
        
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"⚠️ Satellite agent parsing error: {e}")
        
        return {
            "interpretation": "Unable to analyze",
            "severity": "normal",
            "confidence": 0.5
        }
