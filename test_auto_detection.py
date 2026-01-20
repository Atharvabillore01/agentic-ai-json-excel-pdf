#!/usr/bin/env python
"""
Test script to verify auto-detection logic works correctly
"""
import sys
sys.path.insert(0, '/Atharva/agentic-ai/mp-industrial-fastapi')

# Simulate the cache structure
class MockCache:
    def __init__(self):
        self.data = {
            "states": {
                "madhya_pradesh": {},
                "maharashtra": {}
            }
        }
    
    def get(self, key, default):
        return self.data.get(key, default)

cache = MockCache()

def detect_state_from_question(question: str) -> str:
    """
    Auto-detect state from question.
    Looks for state names in the question.
    Falls back to default state if not found.
    """
    question_lower = question.lower()
    available_states = list(cache.get("states", {}).keys())
    
    # Check for state names in question
    for state in available_states:
        state_lower = state.lower()
        # Match full state name or common abbreviations
        if state_lower in question_lower or state.replace("_", " ").lower() in question_lower:
            print(f"✓ Auto-detected state: {state}")
            return state
    
    # Check for common references
    state_mappings = {
        "mp": "madhya_pradesh",
        "madhya pradesh": "madhya_pradesh",
        "maharashtra": "maharashtra",
        "mh": "maharashtra",
    }
    
    for ref, state in state_mappings.items():
        if ref in question_lower and state in available_states:
            print(f"✓ Auto-detected state from reference '{ref}': {state}")
            return state
    
    # Default to madhya_pradesh if no state detected
    default_state = "madhya_pradesh" if "madhya_pradesh" in available_states else available_states[0]
    print(f"✓ No state detected in question, using default: {default_state}")
    return default_state

# Test cases
test_cases = [
    ("What are the industrial parks in Madhya Pradesh?", "madhya_pradesh"),
    ("Tell me about maharashtra policies", "maharashtra"),
    ("MP industrial zones", "madhya_pradesh"),
    ("Show me MH plots", "maharashtra"),
    ("What plots are available?", "madhya_pradesh"),  # Default
    ("madhya_pradesh has many parks", "madhya_pradesh"),
    ("Compare maharashtra and madhya pradesh", "madhya_pradesh"),  # First match wins
]

print("=" * 60)
print("AUTO-DETECTION TEST SUITE")
print("=" * 60)

passed = 0
failed = 0

for question, expected in test_cases:
    print(f"\nTest: {question}")
    result = detect_state_from_question(question)
    
    if result == expected:
        print(f"✓ PASS - Got expected: {expected}")
        passed += 1
    else:
        print(f"✗ FAIL - Expected {expected}, got {result}")
        failed += 1

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("✓ All tests passed!")
    sys.exit(0)
else:
    print("✗ Some tests failed")
    sys.exit(1)
