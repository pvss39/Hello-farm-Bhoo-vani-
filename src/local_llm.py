"""
Ollama LLM integration for enhanced language understanding and generation.
Provides local LLM capabilities for improved intent detection and response generation.
"""

import requests
import json
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()


class OllamaLLM:
    """Interface to local Ollama LLM service."""
    
    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama LLM client.
        
        Args:
            model: Model name (llama3.2:3b, llama3.1:8b, etc.)
            base_url: Ollama server URL
        """
        self.model = model
        self.base_url = base_url
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, stream: bool = False) -> str:
        """
        Generate text using Ollama model.
        
        Args:
            prompt: Input prompt
            stream: Whether to stream response
            
        Returns:
            Generated text
        """
        if not self.available:
            return None
        
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
                "temperature": 0.7,
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                if stream:
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line)
                            full_response += data.get("response", "")
                    return full_response
                else:
                    data = response.json()
                    return data.get("response", "")
            return None
        except Exception as e:
            print(f"❌ Ollama generation error: {e}")
            return None
    
    def understand_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Use LLM to understand farmer intent with better accuracy.
        
        Args:
            user_input: Farmer's message
            
        Returns:
            Dict with detected intent and confidence
        """
        if not self.available:
            return {"intent": None, "confidence": 0}
        
        prompt = f"""Analyze this farmer's message and classify the intent.

Message: "{user_input}"

Classify into ONE of these intents:
- log_irrigation: Farmer is logging/has watered a plot
- check_plot: Farmer wants to know plot status
- satellite_report: Farmer wants satellite/health data
- check_due: Farmer wants to know which plots need water
- help: Farmer is asking for help

Respond ONLY with JSON:
{{
    "intent": "<intent_name>",
    "confidence": 0.0-1.0,
    "plot_keywords": ["plot names mentioned"]
}}"""
        
        response = self.generate(prompt, stream=False)
        
        if response:
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result
            except:
                pass
        
        return {"intent": None, "confidence": 0}
    
    def translate_enhanced(self, text: str, target_language: str = "telugu") -> str:
        """
        Use LLM for better translation quality.
        
        Args:
            text: Text to translate
            target_language: Target language (telugu, english, etc.)
            
        Returns:
            Translated text
        """
        if not self.available:
            return None
        
        prompt = f"""Translate this farming message to {target_language}.
Keep farming terminology accurate. Respond ONLY with the translation.

Original: "{text}"
Translated:"""
        
        response = self.generate(prompt, stream=False)
        return response.strip() if response else None
    
    def generate_response(self, context: Dict[str, Any]) -> str:
        """
        Generate contextual farmer response using LLM.
        
        Args:
            context: Dict with plot_name, status, weather, health, etc.
            
        Returns:
            Generated response
        """
        if not self.available:
            return None
        
        plot_name = context.get("plot_name", "Unknown plot")
        status = context.get("status", "Unknown")
        health = context.get("health", "N/A")
        weather = context.get("weather", "No weather data")
        next_irrigation = context.get("next_irrigation", "N/A")
        
        prompt = f"""Generate a brief, helpful response for an Indian farmer about their plot.

Plot: {plot_name}
Status: {status}
Health Score: {health}
Weather: {weather}
Next Irrigation: {next_irrigation}

Provide practical, actionable advice. Keep response concise (2-3 sentences).
Be friendly and encouraging.

Response:"""
        
        response = self.generate(prompt, stream=False)
        return response.strip() if response else None
    
    def detect_plot_names(self, text: str, known_plots: list = None) -> list:
        """
        Use LLM to detect plot names in text with better accuracy.
        
        Args:
            text: User input text
            known_plots: List of known plot names
            
        Returns:
            List of detected plot names
        """
        if not self.available or not known_plots:
            return []
        
        prompt = f"""Find plot names mentioned in this text.

Known plots: {', '.join(known_plots)}
Text: "{text}"

Respond ONLY with JSON:
{{
    "plots_found": ["plot name 1", "plot name 2"]
}}"""
        
        response = self.generate(prompt, stream=False)
        
        if response:
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result.get("plots_found", [])
            except:
                pass
        
        return []
    
    def health_insights(self, plot_data: Dict[str, Any]) -> str:
        """
        Generate health insights using LLM.
        
        Args:
            plot_data: Dict with plot health metrics
            
        Returns:
            Health insights text
        """
        if not self.available:
            return None
        
        plot_name = plot_data.get("name", "Unknown")
        crop = plot_data.get("crop", "Unknown")
        health_score = plot_data.get("health_score", 0)
        ndvi = plot_data.get("ndvi", 0)
        last_irrigation = plot_data.get("last_irrigation", "Unknown")
        rainfall = plot_data.get("rainfall", "N/A")
        
        prompt = f"""Analyze this farm plot's health and provide brief insights.

Plot: {plot_name}
Crop: {crop}
Health Score: {health_score}/100
NDVI: {ndvi:.2f}
Last Irrigation: {last_irrigation}
Recent Rainfall: {rainfall}

Provide 2-3 actionable insights. Be encouraging.

Insights:"""
        
        response = self.generate(prompt, stream=False)
        return response.strip() if response else None


class OllamaIntegration:
    """Helper class to integrate Ollama into existing agent."""
    
    @staticmethod
    def get_or_init_ollama(model: str = "llama3.2:3b") -> Optional[OllamaLLM]:
        """
        Get Ollama instance if available, None otherwise.
        
        Args:
            model: Model to use
            
        Returns:
            OllamaLLM instance or None
        """
        ollama = OllamaLLM(model=model)
        if ollama.available:
            return ollama
        return None
    
    @staticmethod
    def enhance_intent_detection(base_intent: str, ollama: Optional[OllamaLLM], 
                                 user_input: str, confidence: float = 0.7) -> str:
        """
        Enhance intent detection with LLM if available.
        
        Args:
            base_intent: Original detected intent
            ollama: OllamaLLM instance (optional)
            user_input: User's message
            confidence: Confidence threshold
            
        Returns:
            Final intent
        """
        if not ollama:
            return base_intent
        
        llm_result = ollama.understand_intent(user_input)
        if llm_result.get("confidence", 0) > confidence:
            return llm_result.get("intent", base_intent)
        
        return base_intent
