"""
WOW-6: UNCERTAINTY HANDLER
Manages farmer validation loops when agent is uncertain.

This implements the "ask farmer when unsure" feature - a key differentiator.
When the multi-agent system has low confidence (< 70%), it generates
clarifying questions for farmers instead of giving uncertain recommendations.
"""

from typing import Dict, List, Optional
from src.llm_manager import create_local_llm
import json
import re
import uuid
from datetime import datetime


class UncertaintyHandler:
    """
    Handles uncertain analysis by asking farmers for clarification.
    
    Features:
    - Detects when agent confidence is low (< 70%)
    - Generates contextual questions for farmers
    - Processes farmer responses to update diagnosis
    - Learns from farmer feedback for future accuracy
    """
    
    def __init__(self):
        """Initialize uncertainty handler with LLM access."""
        self.llm = create_local_llm()
        self.pending_questions: Dict[str, Dict] = {}  # Stores questions waiting for response
        self.learning_history: List[Dict] = []  # Track what we learn from farmers
    
    def check_if_uncertain(self, analysis_results: Dict) -> bool:
        """
        Check if any agent is uncertain (confidence < 70%).
        
        Args:
            analysis_results: Output from multi-agent analysis containing
                            confidence scores from each agent
        
        Returns:
            True if should ask farmer for clarification, False if confident
        """
        try:
            # Extract confidence scores from each agent
            satellite_conf = analysis_results.get('satellite_analysis', {}).get('confidence', 1.0)
            weather_conf = analysis_results.get('weather_analysis', {}).get('confidence', 1.0)
            health_conf = analysis_results.get('health_diagnosis', {}).get('confidence', 1.0)
            
            # Find minimum confidence across all agents
            min_confidence = min(satellite_conf, weather_conf, health_conf)
            
            # Return True if any agent is uncertain
            is_uncertain = min_confidence < 0.7
            
            return is_uncertain
        except Exception as e:
            print(f"❌ Error checking uncertainty: {e}")
            return False
    
    def generate_clarification_question(
        self, 
        analysis_results: Dict, 
        plot_name: str, 
        language: str = "telugu"
    ) -> Dict:
        """
        Generate a contextual question for the farmer based on uncertain analysis.
        
        Args:
            analysis_results: Multi-agent analysis output
            plot_name: Name of the plot being analyzed
            language: "telugu" or "english"
        
        Returns:
            Dictionary containing:
            {
                "question_id": "unique_id",
                "question_english": "...",
                "question_telugu": "...",
                "options": ["option1", "option2", ...],
                "context": {satellite/health info}
            }
        """
        try:
            # Extract relevant analysis details
            satellite = analysis_results.get('satellite_analysis', {})
            diagnosis = analysis_results.get('health_diagnosis', {})
            
            # Create system prompt for question generation
            system_prompt = """You are helping create a simple question for a Telugu farmer.

The AI is uncertain about the crop's health status. Generate a simple multiple-choice question
to help the farmer validate or correct the diagnosis.

Respond ONLY with valid JSON:
{
  "question_english": "What did you observe in the field?",
  "question_telugu": "పొలంలో మీరు ఏమి గమనించారు?",
  "options": [
    "Plants look normal and healthy",
    "Some yellowing or browning leaves",
    "Visible insect damage or spots",
    "Water pooling or very dry soil",
    "Don't know / Can't tell"
  ]
}"""
            
            # Build context for the prompt
            context_text = f"""Context:
Plot: {plot_name}
Satellite observation: {satellite.get('interpretation', 'Unable to determine')}
Health diagnosis: {diagnosis.get('diagnosis', 'Uncertain')}
Confidence level: {int(satellite.get('confidence', 0.5) * 100)}%"""
            
            prompt = f"""{context_text}

Generate a simple multiple-choice question to help confirm if the diagnosis is correct."""
            
            # Query LLM for question generation
            response = self.llm.query(
                prompt, 
                system_prompt, 
                temperature=0.3
            )
            
            # Parse JSON response
            try:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    question_data = json.loads(match.group())
                    
                    # Generate unique question ID
                    question_id = str(uuid.uuid4())[:8]
                    
                    # Store pending question with context
                    self.pending_questions[question_id] = {
                        "plot_name": plot_name,
                        "analysis": analysis_results,
                        "timestamp": datetime.now().isoformat(),
                        "language_asked": language
                    }
                    
                    # Add metadata to response
                    question_data["question_id"] = question_id
                    question_data["context"] = {
                        "satellite_ndvi": satellite.get('ndvi'),
                        "satellite_severity": satellite.get('severity'),
                        "diagnosis": diagnosis.get('diagnosis'),
                        "confidence": satellite.get('confidence', 0.5)
                    }
                    
                    return question_data
            except json.JSONDecodeError:
                pass
        except Exception as e:
            print(f"❌ Error generating question: {e}")
        
        # Fallback question if LLM fails
        return {
            "question_id": "fallback_" + str(uuid.uuid4())[:6],
            "question_english": "How does the crop look to you right now?",
            "question_telugu": "ప్రస్తుతం పంట మీకు ఎలా కనిపిస్తుంది?",
            "options": [
                "Very good - healthy plants",
                "Good - mostly normal",
                "Okay - some issues visible",
                "Bad - significant problems",
                "Not sure"
            ],
            "context": analysis_results
        }
    
    def process_farmer_response(
        self, 
        question_id: str, 
        farmer_answer: str
    ) -> Dict:
        """
        Process farmer's answer to improve future predictions.
        
        Uses the farmer's observation to validate or update the AI's diagnosis,
        then learns from this feedback for future accuracy.
        
        Args:
            question_id: ID of the question being answered
            farmer_answer: Farmer's response (text or option selection)
        
        Returns:
            Dictionary containing:
            {
                "learned": True/False,
                "updated_diagnosis": "water_stress"|"pest_damage"|"healthy"|...",
                "confidence_now": 0.95,
                "what_we_learned": "Short summary",
                "recommendation": "Action to take"
            }
        """
        try:
            # Check if question exists
            if question_id not in self.pending_questions:
                return {
                    "learned": False, 
                    "message": "Question not found",
                    "question_id": question_id
                }
            
            # Get original analysis context
            context = self.pending_questions[question_id]
            
            # Create system prompt for learning
            system_prompt = """You are a crop diagnosis system learning from farmer feedback.

The farmer has responded to a diagnostic question. Based on their answer and the original
AI analysis, update the diagnosis.

Respond ONLY with valid JSON:
{
  "updated_diagnosis": "healthy"|"water_stress"|"pest_damage"|"nutrient_deficiency"|"disease"|"unsure",
  "confidence_now": 0.95,
  "what_we_learned": "One sentence summary of what farmer observation taught us",
  "recommendation": "Specific action farmer should take",
  "farmer_agrees": true
}"""
            
            # Build prompt with full context
            prompt = f"""Previous AI Analysis:
Satellite findings: {context['analysis'].get('satellite_analysis', {})}
Health diagnosis: {context['analysis'].get('health_diagnosis', {})}
Plot: {context['plot_name']}

Farmer's Response: "{farmer_answer}"

Based on the farmer's answer, what does this tell us about the actual crop health?
Is the AI diagnosis correct or should it be updated?"""
            
            # Query LLM for learning
            response = self.llm.query(
                prompt, 
                system_prompt, 
                temperature=0.1
            )
            
            # Parse response
            try:
                match = re.search(r'\{.*\}', response, re.DOTALL)
                if match:
                    result = json.loads(match.group())
                    result["learned"] = True
                    
                    # Record this learning event
                    learning_event = {
                        "question_id": question_id,
                        "plot_name": context['plot_name'],
                        "timestamp": datetime.now().isoformat(),
                        "farmer_answer": farmer_answer,
                        "original_diagnosis": context['analysis'].get('health_diagnosis', {}).get('diagnosis'),
                        "updated_diagnosis": result.get('updated_diagnosis'),
                        "confidence_delta": result.get('confidence_now', 0.5) - context['analysis'].get('health_diagnosis', {}).get('confidence', 0.5)
                    }
                    self.learning_history.append(learning_event)
                    
                    # Remove from pending questions
                    del self.pending_questions[question_id]
                    
                    return result
            except json.JSONDecodeError:
                pass
        except Exception as e:
            print(f"❌ Error processing farmer response: {e}")
        
        # Fallback response if LLM fails
        return {
            "learned": False,
            "updated_diagnosis": "requires_manual_review",
            "confidence_now": 0.3,
            "what_we_learned": "Farmer feedback received but could not be processed",
            "recommendation": "Contact farmer directly for clarification"
        }
    
    def get_pending_questions(self) -> Dict[str, Dict]:
        """
        Get all questions waiting for farmer response.
        
        Returns:
            Dictionary mapping question_id to question data
        """
        return self.pending_questions.copy()
    
    def clear_expired_questions(self, hours: int = 24) -> int:
        """
        Clear questions that have been pending for too long.
        
        Args:
            hours: Remove questions older than this many hours
        
        Returns:
            Number of questions cleared
        """
        now = datetime.now()
        expired_ids = []
        
        for question_id, data in self.pending_questions.items():
            try:
                timestamp = datetime.fromisoformat(data['timestamp'])
                age_hours = (now - timestamp).total_seconds() / 3600
                if age_hours > hours:
                    expired_ids.append(question_id)
            except:
                pass
        
        for question_id in expired_ids:
            del self.pending_questions[question_id]
        
        return len(expired_ids)
    
    def get_learning_statistics(self) -> Dict:
        """
        Get statistics about what the system has learned from farmers.
        
        Returns:
            Dictionary with learning metrics
        """
        if not self.learning_history:
            return {
                "total_learning_events": 0,
                "avg_confidence_improvement": 0,
                "most_common_correction": None,
                "farmer_agreement_rate": 0
            }
        
        # Calculate statistics
        total_events = len(self.learning_history)
        
        # Average confidence improvement
        confidence_improvements = [
            e.get('confidence_delta', 0) 
            for e in self.learning_history
        ]
        avg_confidence = sum(confidence_improvements) / len(confidence_improvements) if confidence_improvements else 0
        
        # Most common diagnosis correction
        corrections = [
            e.get('updated_diagnosis') 
            for e in self.learning_history 
            if e.get('updated_diagnosis') != e.get('original_diagnosis')
        ]
        most_common = max(set(corrections), key=corrections.count) if corrections else None
        
        # Farmer agreement rate (when updated diagnosis matches farmer's implied answer)
        agreement_count = sum(
            1 for e in self.learning_history 
            if e.get('original_diagnosis') == e.get('updated_diagnosis')
        )
        agreement_rate = (agreement_count / total_events * 100) if total_events > 0 else 0
        
        return {
            "total_learning_events": total_events,
            "avg_confidence_improvement": round(avg_confidence, 3),
            "most_common_correction": most_common,
            "farmer_agreement_rate": round(agreement_rate, 1),
            "unique_plots_learned_from": len(set(e['plot_name'] for e in self.learning_history))
        }


if __name__ == "__main__":
    # Example usage
    handler = UncertaintyHandler()
    
    # Example analysis results with low confidence
    example_analysis = {
        'satellite_analysis': {
            'interpretation': 'Vegetation looks stressed',
            'confidence': 0.65,
            'ndvi': 0.62,
            'severity': 'moderate'
        },
        'health_diagnosis': {
            'diagnosis': 'possible water stress',
            'confidence': 0.68,
            'uncertainty_reason': 'NDVI slightly low but not critical'
        }
    }
    
    # Check if we should ask farmer
    if handler.check_if_uncertain(example_analysis):
        print("🤔 Analysis is uncertain - generating clarification question\n")
        
        question = handler.generate_clarification_question(
            example_analysis,
            "Thurpu Polam",
            language="telugu"
        )
        
        print(f"❓ Question ID: {question['question_id']}")
        print(f"❓ English: {question['question_english']}")
        print(f"❓ Telugu: {question['question_telugu']}")
        print(f"📋 Options: {question['options']}\n")
        
        # Simulate farmer response
        farmer_response = "Some yellowing or browning leaves"
        print(f"👨‍🌾 Farmer says: {farmer_response}\n")
        
        # Process response
        result = handler.process_farmer_response(question['question_id'], farmer_response)
        print(f"✅ Learning Result:")
        print(f"   Updated Diagnosis: {result.get('updated_diagnosis')}")
        print(f"   New Confidence: {result.get('confidence_now')}")
        print(f"   What we learned: {result.get('what_we_learned')}")
        print(f"   Recommendation: {result.get('recommendation')}\n")
        
        # Show learning statistics
        stats = handler.get_learning_statistics()
        print(f"📊 Learning Statistics:")
        print(f"   Total events: {stats['total_learning_events']}")
        print(f"   Avg confidence improvement: {stats['avg_confidence_improvement']}")
