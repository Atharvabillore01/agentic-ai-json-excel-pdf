"""
LLM Provider Factory - Switches between Groq and OpenAI
Unified interface for both providers
"""

import logging
from typing import Dict, Any
from enum import Enum
from app.core import settings
from app.services.groq_client import groq_chat

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers"""
    GROQ = "groq"
    OPENAI = "openai"


class LLMFactory:
    """Factory for creating LLM clients"""
    
    @staticmethod
    def get_provider() -> LLMProvider:
        """Get configured LLM provider"""
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "openai":
            return LLMProvider.OPENAI
        elif provider == "groq":
            return LLMProvider.GROQ
        else:
            logger.warning(f"Unknown provider {provider}, defaulting to Groq")
            return LLMProvider.GROQ
    
    @staticmethod
    def get_client():
        """Get appropriate LLM client"""
        provider = LLMFactory.get_provider()
        
        if provider == LLMProvider.OPENAI:
            from app.services.openai_client import get_openai_client
            logger.info("Using OpenAI client")
            return get_openai_client()
        else:
            from app.services.groq_client import get_groq_client
            logger.info("Using Groq client")
            return get_groq_client()
    
    @staticmethod
    def query(prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """
        Query the configured LLM provider
        
        Args:
            prompt: The prompt to query
            max_tokens: Maximum tokens in response
            temperature: Creativity level
        
        Returns:
            Response from LLM
        """
        client = LLMFactory.get_client()
        return client.query(prompt, max_tokens, temperature)
    
    @staticmethod
    def generate_investor_response(question: str, context_data: str = "") -> Dict[str, Any]:
        """
        Generate investor-focused response using configured provider
        
        Args:
            question: User's question
            context_data: Optional context
        
        Returns:
            Structured response
        """
        client = LLMFactory.get_client()
        provider = LLMFactory.get_provider()
        
        try:
            if provider == LLMProvider.OPENAI:
                return client.generate_investor_response(question, context_data)
            else:
                # Groq client uses query method
                response = client.query(
                    f"Context:\n{context_data}\n\nQuestion: {question}",
                    max_tokens=1500,
                    temperature=0.6
                )
                return {
                    "status": "success",
                    "answer": response,
                    "model": settings.GROQ_MODEL,
                    "provider": "groq"
                }
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "provider": provider.value
            }
    
    @staticmethod
    def get_model_info() -> Dict[str, Any]:
        """Get information about current LLM configuration"""
        provider = LLMFactory.get_provider()
        
        if provider == LLMProvider.OPENAI:
            return {
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "status": "configured" if settings.OPENAI_API_KEY else "not_configured"
            }
        else:
            return {
                "provider": "groq",
                "model": settings.GROQ_MODEL,
                "status": "configured" if settings.GROQ_API_KEY else "not_configured"
            }
    
    @staticmethod
    def validate_configuration() -> Dict[str, bool]:
        """Validate LLM configuration"""
        provider = LLMFactory.get_provider()
        
        validation = {
            "provider_selected": True,
            "groq_configured": bool(settings.GROQ_API_KEY),
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "current_provider": provider.value,
        }
        
        if provider == LLMProvider.OPENAI:
            validation["provider_ready"] = bool(settings.OPENAI_API_KEY)
        else:
            validation["provider_ready"] = bool(settings.GROQ_API_KEY)
        
        logger.info(f"LLM Configuration: {validation}")
        return validation


class LLMConfig:
    """Configuration for LLM providers"""
    
    # OpenAI Models
    OPENAI_MODELS = {
        "gpt-4o": {
            "name": "GPT-4o",
            "max_tokens": 4096,
            "context_window": 128000,
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
        },
        "gpt-4o-mini": {
            "name": "GPT-4o Mini",
            "max_tokens": 4096,
            "context_window": 128000,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.0006,
        }
    }
    
    # Groq Models
    GROQ_MODELS = {
        "mixtral-8x7b-32768": {
            "name": "Mixtral 8x7B",
            "max_tokens": 32768,
            "context_window": 32768,
            "cost_per_1k_input": 0.00024,
            "cost_per_1k_output": 0.00024,
        },
        "llama2-70b-4096": {
            "name": "Llama 2 70B",
            "max_tokens": 4096,
            "context_window": 4096,
            "cost_per_1k_input": 0.0008,
            "cost_per_1k_output": 0.0008,
        }
    }
    
    @staticmethod
    def get_openai_models() -> Dict[str, Dict]:
        """Get available OpenAI models"""
        return LLMConfig.OPENAI_MODELS
    
    @staticmethod
    def get_groq_models() -> Dict[str, Dict]:
        """Get available Groq models"""
        return LLMConfig.GROQ_MODELS
    
    @staticmethod
    def get_model_specs(provider: str, model: str) -> Dict:
        """Get specifications for a model"""
        if provider.lower() == "openai":
            return LLMConfig.OPENAI_MODELS.get(model, {})
        elif provider.lower() == "groq":
            return LLMConfig.GROQ_MODELS.get(model, {})
        return {}


def get_llm_factory() -> LLMFactory:
    """Get LLM factory"""
    return LLMFactory()
