"""Farmer communication agent for translating technical analysis"""

from typing import Dict
from src.llm_manager import create_local_llm


class FarmerCommunicationAgent:
    """Specializes in communicating findings to farmers."""
    
    def __init__(self):
        """Initialize farmer communication specialist."""
        self.llm = create_local_llm()
        self.name = "Farmer Communication"
    
    def translate_to_farmer(
        self, 
        satellite: Dict, 
        weather: Dict, 
        diagnosis: Dict, 
        farmer_language: str = "telugu"
    ) -> str:
        """
        Convert technical analysis to farmer-friendly language.
        
        Args:
            satellite: Satellite analysis results
            weather: Weather analysis results
            diagnosis: Health diagnosis results
            farmer_language: Language for farmer ("english" or "telugu")
            
        Returns:
            Simple, actionable message in farmer's language
        """
        system_prompt = f"""You are {self.name}, bridging technical agriculture data and farmer understanding.

Your ONLY job: Explain findings in simple, actionable language.

Farmer speaks: {farmer_language}
Do NOT use technical jargon like "NDVI", "chlorophyll", "reflectance"
Use simple farming terms they understand.

Respond with a clear, friendly message in {farmer_language}."""
        
        prompt = f"""Technical findings:
- Satellite: {satellite.get('interpretation', '')} ({satellite.get('severity', 'normal')})
- Weather: {weather.get('recommendation', '')} - {weather.get('reasoning', '')}
- Diagnosis: {diagnosis.get('diagnosis', '')}
- Actions: {diagnosis.get('recommended_actions', [])}
- Urgency: {diagnosis.get('urgency', 'low')}

Translate this into a simple message for the farmer."""
        
        response = self.llm.query(prompt, system_prompt, temperature=0.3)
        return response
