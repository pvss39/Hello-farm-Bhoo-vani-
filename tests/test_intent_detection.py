"""
Intelligent intent detection test

Tests WOW-2: LLM-based intent understanding for natural language inputs.
"""

from src.agent import FarmAgent

print("🔧 Testing WOW-2: Intelligent Intent Detection\n")
print("=" * 60)

agent = FarmAgent(use_ollama=True)

test_inputs = [
    "I gave water to the field near temple",
    "నేను తూర్పు పొలానికి నీరు పోశాను",
    "Show athota status",
    "Get me satellite data for munnagi"
]

for inp in test_inputs:
    print(f"\n📝 Input: {inp}")
    
    state = {
        'messages': [],
        'user_input': inp,
        'detected_language': '',
        'plot_name': '',
        'action': '',
        'response_english': '',
        'response_telugu': '',
        'final_response': ''
    }
    
    state = agent.understand_intent(state)
    print(f"   ✓ Action: {state['action']}")
    print(f"   ✓ Plot: {state['plot_name']}")

print("\n" + "=" * 60)
print("✅ WOW-2 Verification Complete!")
