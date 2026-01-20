#!/usr/bin/env python
"""
Test Suite for Fact Verification and OpenAI Integration
Tests verification logic, response categorization, and LLM provider switching
"""

import sys
sys.path.insert(0, '/Atharva/agentic-ai/mp-industrial-fastapi')

from app.core.response_categorizer import get_response_categorizer, ResponseCategorizer
from app.core.fact_verification import get_fact_verifier, DataType, VerificationLevel
from app.services.llm_factory import LLMFactory, LLMConfig
from app.core import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# RESPONSE CATEGORIZER TESTS
# ============================================================================

def test_response_categorizer():
    """Test response categorization system"""
    print("\n" + "="*70)
    print("RESPONSE CATEGORIZER TESTS")
    print("="*70)
    
    categorizer = get_response_categorizer()
    
    test_cases = [
        {
            "name": "Distance Claim Detection",
            "text": "The plot is 5 km from the railway station",
            "expected_claims": ["distance"]
        },
        {
            "name": "Price Claim Detection",
            "text": "The plot costs ₹50 lakhs per acre",
            "expected_claims": ["price"]
        },
        {
            "name": "Availability Claim Detection",
            "text": "Plot 123 is currently available",
            "expected_claims": ["availability"]
        },
        {
            "name": "Coordinate Claim Detection",
            "text": "Location coordinates: 23.1815°N 79.9864°E",
            "expected_claims": ["coordinate"]
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        claims = categorizer.detect_factual_claims(test["text"])
        
        has_claims = any(len(v) > 0 for k, v in claims.items() if k.endswith("_claims"))
        
        if has_claims:
            print(f"✓ PASS - Detected factual claims")
            print(f"  Claims: {claims}")
            passed += 1
        else:
            print(f"✗ FAIL - No claims detected")
            failed += 1
    
    return passed, failed


def test_response_categorization():
    """Test response section categorization"""
    print("\n" + "="*70)
    print("RESPONSE CATEGORIZATION TESTS")
    print("="*70)
    
    categorizer = get_response_categorizer()
    
    sample_response = """
VERIFIED INFORMATION:
- Madhya Pradesh has multiple industrial parks
- The state offers tax incentives for manufacturing
- Infrastructure includes railway and road networks

REQUIRES USER INPUT:
- Specific plot size requirement
- Investment budget
- Preferred location within the state

UNAVAILABLE / CANNOT BE DETERMINED:
- Exact distance without knowing specific plot location
- Current market prices for specific plots
- Infrastructure proximity without verified coordinates
"""
    
    print("\nSample Response:")
    print(sample_response)
    
    category = categorizer.categorize(sample_response)
    
    print("\nCategorization Results:")
    print(f"✓ Verified Information Items: {len(category.verified_information)}")
    for item in category.verified_information:
        print(f"  - {item[:60]}...")
    
    print(f"\n✓ Requires User Input: {len(category.requires_user_input)}")
    for item in category.requires_user_input:
        print(f"  - {item[:60]}...")
    
    print(f"\n✓ Unavailable Data: {len(category.unavailable_data)}")
    for item in category.unavailable_data:
        print(f"  - {item[:60]}...")
    
    return 1, 0


# ============================================================================
# FACT VERIFICATION TESTS
# ============================================================================

def test_fact_verification():
    """Test fact verification system"""
    print("\n" + "="*70)
    print("FACT VERIFICATION TESTS")
    print("="*70)
    
    verifier = get_fact_verifier(VerificationLevel.STRICT)
    
    test_cases = [
        {
            "name": "Distance Verification",
            "claim": "Plot XYZ is 5 km from Central Railway Station",
            "expected_type": DataType.DISTANCE,
        },
        {
            "name": "Price Verification",
            "claim": "The plot is priced at ₹50 lakhs per acre",
            "expected_type": DataType.PRICE,
        },
        {
            "name": "Availability Verification",
            "claim": "Plot 456 is currently available in the park",
            "expected_type": DataType.AVAILABILITY,
        },
        {
            "name": "Infrastructure Verification",
            "claim": "The site is close to the airport",
            "expected_type": DataType.INFRASTRUCTURE,
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        detected_type = verifier.categorize_data_type(test["claim"])
        should_verify, reason = verifier.should_request_verification(test["claim"])
        
        if detected_type == test["expected_type"] and should_verify:
            print(f"✓ PASS")
            print(f"  Detected Type: {detected_type.value}")
            print(f"  Requires Verification: {should_verify}")
            print(f"  Reason: {reason}")
            passed += 1
        else:
            print(f"✗ FAIL")
            print(f"  Expected: {test['expected_type'].value}, Got: {detected_type.value}")
            failed += 1
    
    return passed, failed


def test_verification_response_building():
    """Test verification response recommendations"""
    print("\n" + "="*70)
    print("VERIFICATION RESPONSE BUILDING TESTS")
    print("="*70)
    
    verifier = get_fact_verifier(VerificationLevel.STRICT)
    
    data_types = [DataType.DISTANCE, DataType.PRICE, DataType.AVAILABILITY]
    
    for data_type in data_types:
        print(f"\nData Type: {data_type.value.upper()}")
        response = verifier.build_verification_response(
            f"Sample {data_type.value} claim",
            data_type
        )
        
        print(f"  Type: {response.get('type')}")
        print(f"  Message: {response.get('message')}")
        print(f"  Required Inputs:")
        for inp in response.get('required_inputs', []):
            print(f"    - {inp}")
        print(f"  Reason: {response.get('reason')}")
    
    return 1, 0


# ============================================================================
# LLM PROVIDER FACTORY TESTS
# ============================================================================

def test_llm_factory():
    """Test LLM factory and provider switching"""
    print("\n" + "="*70)
    print("LLM PROVIDER FACTORY TESTS")
    print("="*70)
    
    # Test provider detection
    print("\nTest 1: Provider Configuration Detection")
    provider = LLMFactory.get_provider()
    print(f"✓ Current Provider: {provider.value}")
    print(f"  LLM_PROVIDER env: {settings.LLM_PROVIDER}")
    
    # Test model info
    print("\nTest 2: Model Information")
    model_info = LLMFactory.get_model_info()
    print(f"✓ Provider: {model_info.get('provider')}")
    print(f"  Model: {model_info.get('model')}")
    print(f"  Status: {model_info.get('status')}")
    
    # Test configuration validation
    print("\nTest 3: Configuration Validation")
    validation = LLMFactory.validate_configuration()
    print(f"✓ Provider Selected: {validation.get('provider_selected')}")
    print(f"  Groq Configured: {validation.get('groq_configured')}")
    print(f"  OpenAI Configured: {validation.get('openai_configured')}")
    print(f"  Current Provider Ready: {validation.get('provider_ready')}")
    print(f"  Current Provider: {validation.get('current_provider')}")
    
    return 1, 0


def test_llm_config():
    """Test LLM configuration and model specs"""
    print("\n" + "="*70)
    print("LLM CONFIGURATION TESTS")
    print("="*70)
    
    # Test OpenAI models
    print("\nOpenAI Models Available:")
    openai_models = LLMConfig.get_openai_models()
    for model_name, specs in openai_models.items():
        print(f"  ✓ {specs.get('name')} ({model_name})")
        print(f"    Max Tokens: {specs.get('max_tokens')}")
        print(f"    Context Window: {specs.get('context_window')}")
    
    # Test Groq models
    print("\nGroq Models Available:")
    groq_models = LLMConfig.get_groq_models()
    for model_name, specs in groq_models.items():
        print(f"  ✓ {specs.get('name')} ({model_name})")
        print(f"    Max Tokens: {specs.get('max_tokens')}")
        print(f"    Context Window: {specs.get('context_window')}")
    
    # Test model specs retrieval
    print("\nTest: Get Model Specifications")
    openai_specs = LLMConfig.get_model_specs("openai", "gpt-4o")
    print(f"✓ GPT-4o Specs Retrieved")
    print(f"  Context Window: {openai_specs.get('context_window')}")
    print(f"  Max Tokens: {openai_specs.get('max_tokens')}")
    
    return 1, 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_response_safety():
    """Test response safety checking"""
    print("\n" + "="*70)
    print("RESPONSE SAFETY TESTS")
    print("="*70)
    
    categorizer = get_response_categorizer()
    
    test_cases = [
        {
            "name": "Safe Response with Disclaimers",
            "text": "I don't have sufficient verified data for specific distances. However, the park is generally known to be near infrastructure.",
            "expected_safe": True
        },
        {
            "name": "Unsafe Response with Hallucinated Facts",
            "text": "Plot 123 is exactly 2.5 km from Central Station and costs ₹45 lakhs per acre.",
            "expected_safe": False
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        is_safe = categorizer.is_response_safe(test["text"])
        
        print(f"  Response Safe: {is_safe}")
        print(f"  Expected: {test['expected_safe']}")
        
        if is_safe == test["expected_safe"]:
            print(f"✓ PASS")
            passed += 1
        else:
            print(f"✗ FAIL")
            failed += 1
    
    return passed, failed


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("FACT VERIFICATION AND OPENAI INTEGRATION TEST SUITE")
    print("="*70)
    
    results = []
    
    # Response Categorizer Tests
    p, f = test_response_categorizer()
    results.append(("Response Categorizer", p, f))
    
    p, f = test_response_categorization()
    results.append(("Response Categorization", p, f))
    
    # Fact Verification Tests
    p, f = test_fact_verification()
    results.append(("Fact Verification", p, f))
    
    p, f = test_verification_response_building()
    results.append(("Verification Responses", p, f))
    
    # LLM Factory Tests
    p, f = test_llm_factory()
    results.append(("LLM Factory", p, f))
    
    p, f = test_llm_config()
    results.append(("LLM Configuration", p, f))
    
    # Integration Tests
    p, f = test_response_safety()
    results.append(("Response Safety", p, f))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    total_passed = sum(r[1] for r in results)
    total_failed = sum(r[2] for r in results)
    
    for test_name, passed, failed in results:
        status = "✓" if failed == 0 else "✗"
        print(f"{status} {test_name:.<40} {passed} passed, {failed} failed")
    
    print("\n" + "="*70)
    print(f"TOTAL: {total_passed} passed, {total_failed} failed")
    print("="*70)
    
    if total_failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n✗ {total_failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
