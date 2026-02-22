"""
Translation service for English-Telugu conversion.
Provides dual-language message formatting for farmer notifications.
"""

from typing import Literal
import json
import os


class LanguageManager:
    """Handles English-Telugu translation and language detection."""
    
    def __init__(self):
        """Initialize translation dictionary."""
        self.telugu_keywords = [
            'నీరు', 'పోశాను', 'పారుదల', 'చేశాను', 'ఎలా', 'చూపించు',
            'ఆరోగ్యం', 'రిపోర్ట్', 'కావాలా', 'అవసరమా', 'పొలం',
            'జొన్న', 'తూర్పు', 'ఆత్తోట', 'ముణగి'
        ]
        
        # Basic translation dictionary for common phrases
        self.translation_dict = {
            'Good morning': 'శుభోదయం',
            'Field': 'పొలం',
            'Plant health': 'మొక్కల ఆరోగ్యం',
            'Last irrigation': 'చివరి నీటిపారుదల',
            'Next irrigation': 'తదుపరి నీరు',
            'Water needed': 'నీరు అవసరం',
            'Irrigation logged': 'నీటిపారుదల నమోదు',
            'Status': 'స్థితి',
            'Healthy': 'మంచిది',
            'Stress': 'ఒత్తిడి',
            'Days ago': 'రోజుల క్రితం',
            'In days': 'రోజుల్లో',
            'days': 'రోజులు',
            'Weather': 'వాతావరణం',
            'Temperature': 'ఉష్ణోగ్రత',
            'Humidity': 'ఆర్ద్రత',
            'Rainfall': 'వర్షం',
            'Sunny': 'ఎండ',
            'Cloudy': 'మేఘాలు',
            'Rainy': 'వర్షం',
            'No rain expected': 'వర్షం లేదు',
            'Health report': 'ఆరోగ్య నివేదిక',
            'Crop': 'పంట',
            'Jowar': 'జొన్న',
        }
    
    def translate_en_to_te(self, text: str) -> str:
        """
        Translate English text to Telugu using dictionary lookup.
        
        Args:
            text: English text to translate
            
        Returns:
            Telugu translation or original text if translation fails
        """
        try:
            result = text
            for en_phrase, te_phrase in self.translation_dict.items():
                result = result.replace(en_phrase, te_phrase)
            return result
        except Exception as e:
            print(f"⚠️ Translation error (EN→TE): {e}")
            return text
    
    def translate_te_to_en(self, text: str) -> str:
        """
        Translate Telugu text to English using dictionary lookup.
        
        Args:
            text: Telugu text to translate
            
        Returns:
            English translation or original text if translation fails
        """
        try:
            result = text
            for en_phrase, te_phrase in self.translation_dict.items():
                result = result.replace(te_phrase, en_phrase)
            return result
        except Exception as e:
            print(f"⚠️ Translation error (TE→EN): {e}")
            return text
    
    def detect_language(self, text: str) -> Literal['telugu', 'english', 'mixed']:
        """
        Detect if input is Telugu, English, or mixed language.
        
        Args:
            text: Input text to detect
            
        Returns:
            'telugu', 'english', or 'mixed'
        """
        telugu_count = sum(1 for keyword in self.telugu_keywords if keyword in text)
        english_words = len(text.split())
        
        if telugu_count > 2:
            return 'telugu'
        elif english_words > telugu_count:
            return 'english'
        else:
            return 'mixed'
    
    def format_dual_message(self, english_text: str) -> str:
        """
        Format message with English and Telugu translation.
        
        Args:
            english_text: English message
            
        Returns:
            Formatted string with English + separator + Telugu
        """
        try:
            telugu_text = self.translate_en_to_te(english_text)
            return f"{english_text}\n\n---\n\n{telugu_text}"
        except Exception as e:
            print(f"⚠️ Format error: {e}")
            return english_text
