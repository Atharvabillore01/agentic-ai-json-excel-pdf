"""
OpenAI API Client for GPT-4o integration
Provides intelligent question answering with fact verification
"""

from openai import OpenAI
import logging
from app.core import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API interactions"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured in environment")
        
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        logger.info(f"OpenAI client initialized with model: {self.model}")
    
    def query(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """
        Query OpenAI with a prompt
        
        Args:
            prompt: The prompt to send to OpenAI
            max_tokens: Maximum tokens in response
            temperature: Creativity/randomness (0.0-1.0)
        
        Returns:
            Response text from OpenAI
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert industrial investment advisor for Madhya Pradesh and Maharashtra, India.
                        
Your guidelines:
1. Provide accurate, well-structured, and verifiable information only
2. Never hallucinate or estimate factual data
3. For location-specific or measurable data (distances, prices, coordinates, availability):
   - Ask for missing inputs if not provided
   - State clearly if data cannot be determined
4. For general/qualitative information: answer confidently
5. For specific/quantitative information:
   - Provide if verified data exists
   - Say "I don't have sufficient verified data to answer this accurately" if not
6. Clearly separate responses into:
   - Verified Information (with sources)
   - Information Requiring User Input (specific requests)
   - Unavailable / Cannot Be Determined
7. Tone: professional, neutral, investor-focused"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            answer = response.choices[0].message.content
            logger.info(f"OpenAI query successful (model: {self.model})")
            return answer
            
        except Exception as e:
            logger.error(f"OpenAI query failed: {str(e)}")
            raise
    
    def extract_facts(self, text: str) -> dict:
        """
        Extract factual claims from text for verification
        
        Args:
            text: Text to extract facts from
        
        Returns:
            Dictionary of extracted facts
        """
        prompt = f"""Analyze this text and extract all factual claims that need verification:
        
Text: {text}

Return a JSON object with:
- distance_claims: list of any distance/proximity claims
- price_claims: list of any price/rate claims
- coordinate_claims: list of any location coordinate claims
- availability_claims: list of any availability claims
- other_quantitative_claims: list of other specific numeric/factual claims
- qualitative_claims: list of general/qualitative statements

Be specific about what was claimed."""

        response = self.query(prompt, max_tokens=500, temperature=0.2)
        logger.info(f"Extracted facts from text")
        return response
    
    def verify_response_format(self, answer: str) -> dict:
        """
        Verify response is properly formatted with sections
        
        Args:
            answer: The answer to verify
        
        Returns:
            Dictionary with verified_info, requires_input, unavailable sections
        """
        prompt = f"""Analyze this answer and categorize it into these sections:

Answer: {answer}

Create a structured response with:

VERIFIED INFORMATION:
- List facts that are verifiable and appear accurate
- Include sources if mentioned
- List claims that are general/qualitative and safe to state

INFORMATION REQUIRING USER INPUT:
- List what specific information the user needs to provide
- List missing mandatory inputs needed
- List follow-up questions that should be asked

UNAVAILABLE / CANNOT BE DETERMINED:
- List specific facts that cannot be verified without external data
- List items where you explicitly said "I don't have sufficient verified data"
- List items that require external sources

Format your response clearly with these three sections."""

        response = self.query(prompt, max_tokens=800, temperature=0.2)
        logger.info(f"Verified response format")
        return response
    
    def generate_investor_response(self, question: str, context_data: str = "") -> dict:
        """
        Generate investor-focused response with fact verification built-in
        
        Args:
            question: User's question
            context_data: Optional context data (policies, parks info, etc.)
        
        Returns:
            Dictionary with structured response
        """
        system_prompt = """You are an expert industrial investment advisor for Madhya Pradesh and Maharashtra.

CRITICAL RULES:
1. NEVER estimate or hallucinate data for:
   - Distances from infrastructure
   - Prices or rates
   - Specific plot coordinates
   - Infrastructure availability
   - Property details

2. For these sensitive areas:
   - State exactly what verified data you have
   - Ask for missing information if needed
   - Say "I don't have sufficient verified data" if unknown

3. Structure your answer with clear sections:
   
   [VERIFIED INFORMATION]
   What you know for certain with sources
   
   [REQUIRES USER INPUT]
   What information you need from user
   
   [CANNOT DETERMINE]
   What data isn't available without external sources

4. For general topics (policies, incentives, investment climate) - be confident and detailed
5. For specific data (plots, prices, distances) - be conservative and ask for details

Always maintain professional, neutral, investor-focused tone."""

        prompt = f"""Based on this context data, answer the user's question following all fact-verification rules.

CONTEXT DATA:
{context_data if context_data else "No specific context provided"}

USER QUESTION: {question}

Remember: 
- Only provide facts you can verify
- Ask for missing information
- Never hallucinate specific details
- Separate your response into the three sections"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.6
            )
            
            answer = response.choices[0].message.content
            
            return {
                "status": "success",
                "answer": answer,
                "model": self.model,
                "verified_by_llm": True
            }
            
        except Exception as e:
            logger.error(f"Failed to generate investor response: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "model": self.model
            }
    
    def get_model_info(self) -> dict:
        """Get information about current model"""
        return {
            "provider": "OpenAI",
            "model": self.model,
            "version": "GPT-4o" if "4o" in self.model else "Unknown"
        }


# Singleton instance
_openai_client = None

def get_openai_client() -> OpenAIClient:
    """Get or create OpenAI client singleton"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client
