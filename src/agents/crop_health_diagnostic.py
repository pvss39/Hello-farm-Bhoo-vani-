"""Crop health diagnostic agent for identifying plant health issues"""

from typing import Dict
from src.llm_manager import create_local_llm
import json
import re


class CropHealthDiagnosticAgent:
    """Specializes in diagnosing crop health issues."""
    
    def __init__(self):
        """Initialize crop health diagnostic specialist."""
        self.llm = create_local_llm()
        self.name = "Crop Health Diagnostic"
    
    def diagnose(self, satellite_analysis: Dict, weather_analysis: Dict, crop_type: str) -> Dict:
        """
        Diagnose potential crop health issues.
        
        Args:
            satellite_analysis: Analysis from satellite agent
            weather_analysis: Analysis from weather agent
            crop_type: Type of crop (e.g., "Jowar")
            
        Returns:
            {
                "diagnosis": "healthy"|"water_stress"|"nutrient_deficiency"|"pest_damage"|"disease",
                "recommended_actions": ["action1", "action2"],
                "urgency": "low"|"medium"|"high"
            }
        """
        system_prompt = f"""You are {self.name}, a plant pathologist and agronomist.

Your ONLY job: Diagnose health issues in {crop_type} crops.

Respond ONLY with valid JSON:
{{
  "diagnosis": "healthy"|"water_stress"|"nutrient_deficiency"|"pest_damage"|"disease",
  "recommended_actions": ["action1", "action2"],
  "urgency": "low"|"medium"|"high"
}}"""
        
        prompt = f"""Crop: {crop_type}
Satellite finding: {satellite_analysis.get('interpretation', 'unknown')}
Severity: {satellite_analysis.get('severity', 'normal')}
Weather recommendation: {weather_analysis.get('recommendation', 'unknown')}

What is your diagnosis?"""
        
        response = self.llm.query(prompt, system_prompt, temperature=0.2)
        
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"⚠️ Diagnostic agent parsing error: {e}")
        
        return {
            "diagnosis": "healthy",
            "recommended_actions": ["Continue monitoring"],
            "urgency": "low"
        }
