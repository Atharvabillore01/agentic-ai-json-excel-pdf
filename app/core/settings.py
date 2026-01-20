import os
from dotenv import load_dotenv

load_dotenv()  # <-- THIS LINE FIXES EVERYTHING

# API Configuration
DEBUG_API = os.getenv("DEBUG_API", "false").lower() == "true"

# LLM Provider Selection (groq or openai)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# Validation
if LLM_PROVIDER not in ["groq", "openai"]:
    raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}")


# Fact Verification Settings
ENFORCE_FACT_VERIFICATION = os.getenv("ENFORCE_FACT_VERIFICATION", "true").lower() == "true"
REQUIRE_USER_INPUT_FOR_SPECIFIC_DATA = os.getenv("REQUIRE_USER_INPUT_FOR_SPECIFIC_DATA", "true").lower() == "true"

# Validate LLM provider
if LLM_PROVIDER not in ["groq", "openai"]:
    raise ValueError(f"Invalid LLM_PROVIDER: {LLM_PROVIDER}. Must be 'groq' or 'openai'")
