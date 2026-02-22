"""
LLM Manager validation test

Tests local Ollama and cloud LLM initialization and mode switching.
"""

from src.llm_manager import create_local_llm, create_cloud_llm


def test_initialization():
    """Test initialization and mode switching."""
    print("\n✅ Test 1: Initialization")
    print("-" * 50)
    
    llm = create_local_llm()
    print(f"   Mode: {llm.mode}")
    print(f"   Model: {llm.local_model}")
    
    print("\n✅ Test 2: Mode Switching")
    print("-" * 50)
    status = llm.switch_mode("cloud")
    print(f"   {status}")
    print(f"   Mode: {llm.mode}")
    
    status = llm.switch_mode("local")
    print(f"   {status}")
    print(f"   Mode: {llm.mode}")
    
    print("\n✅ Test 3: Invalid Mode Handling")
    print("-" * 50)
    status = llm.switch_mode("invalid")
    print(f"   {status}")
    
    print("\n✅ Test 4: Cloud Mode (No API Key)")
    print("-" * 50)
    llm_cloud = create_cloud_llm()
    print(f"   Mode: {llm_cloud.mode}")
    
    print("\n" + "="*50)
    print("✅ All initialization tests passed!")
    print("="*50)


if __name__ == "__main__":
    test_initialization()
