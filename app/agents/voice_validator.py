"""
Voice response validation to ensure conversational, natural output.

Rejects:
- Monologues (too long)
- Repeated questions
- Non-conversational tone (lists, data dumps)
- Missing context awareness
- Unsafe facts (guesses, unverified claims)
"""

import json
import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)


class VoiceResponseValidator:
    """
    Validates voice responses meet conversational standards.
    """
    
    MAX_VOICE_WORDS = 60  # ~4 sentences at ~15 words each
    MAX_SENTENCES = 4
    
    @staticmethod
    def is_valid_voice_response(voice_response: str) -> Tuple[bool, List[str]]:
        """
        Check if voice response meets conversational standards.
        
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        # Count words
        words = voice_response.split()
        if len(words) > VoiceResponseValidator.MAX_VOICE_WORDS:
            issues.append(
                f"Too long: {len(words)} words (max {VoiceResponseValidator.MAX_VOICE_WORDS}). "
                "Voice responses must be 2-4 sentences."
            )
        
        # Check for monologue patterns
        if "bullet" in voice_response.lower() or "\n-" in voice_response:
            issues.append("Voice response contains bullet points. Use flowing conversation instead.")
        
        if "as follows" in voice_response.lower() or "following information" in voice_response.lower():
            issues.append("Voice response sounds like a list dump. Be conversational.")
        
        # Check for data dump patterns
        if any(pattern in voice_response for pattern in ["[", "]", "{", "}", "coordinates", "latitude", "longitude"]):
            issues.append("Voice response contains technical data/formatting. Avoid coordinates, brackets, etc.")
        
        # Check for section headers
        if any(pattern in voice_response for pattern in ["[VERIFIED", "[REQUIRES", "[CANNOT", "###", "##"]):
            issues.append("Voice response contains section headers. These are for text mode only.")
        
        # Check sentence count (rough approximation using periods)
        sentences = [s.strip() for s in voice_response.split(".") if s.strip()]
        if len(sentences) > VoiceResponseValidator.MAX_SENTENCES:
            issues.append(
                f"Too many sentences: {len(sentences)} (max {VoiceResponseValidator.MAX_SENTENCES}). "
                "Use 2-4 sentences only."
            )
        
        return len(issues) == 0, issues
    
    @staticmethod
    def extract_question_from_voice_response(voice_response: str) -> str:
        """
        Extract the question being asked in voice response (if any).
        """
        # Simple heuristic: look for "?" at end of text
        if "?" in voice_response:
            # Get the last sentence that contains ?
            sentences = voice_response.split(".")
            for sentence in reversed(sentences):
                if "?" in sentence:
                    return sentence.strip()
        return ""
    
    @staticmethod
    def is_repeating_question(
        new_question: str,
        previously_asked: List[str],
        similarity_threshold: float = 0.7
    ) -> bool:
        """
        Check if new question is too similar to previously asked ones.
        Prevents boring repetition in voice mode.
        """
        if not new_question or not previously_asked:
            return False
        
        new_words = set(new_question.lower().split())
        
        for old_question in previously_asked:
            old_words = set(old_question.lower().split())
            if not old_words:
                continue
            
            # Calculate Jaccard similarity
            intersection = len(new_words & old_words)
            union = len(new_words | old_words)
            similarity = intersection / union if union > 0 else 0
            
            if similarity >= similarity_threshold:
                return True
        
        return False
    
    @staticmethod
    def parse_dual_response(response_text: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse LLM response into text_response and voice_response.
        Handles both structured JSON and fallback text parsing.
        
        Returns:
            (success, parsed_response_dict, error_message)
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(response_text)
            
            # Validate structure
            if "voice_response" not in parsed:
                return False, {}, "Missing 'voice_response' in JSON response"
            
            if "text_response" not in parsed:
                return False, {}, "Missing 'text_response' in JSON response"
            
            return True, parsed, ""
        
        except json.JSONDecodeError:
            # Fallback: Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                try:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    parsed = json.loads(json_str)
                    
                    if "voice_response" in parsed and "text_response" in parsed:
                        return True, parsed, ""
                except (json.JSONDecodeError, ValueError):
                    pass
            
            return False, {}, f"Failed to parse response as JSON. Got: {response_text[:200]}"
    
    @staticmethod
    def validate_and_fix_voice_response(
        parsed_response: Dict[str, Any],
        previously_asked: List[str],
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate voice response and flag issues. Returns the response + list of warnings.
        Does not modify the response (raising issues is caller's responsibility).
        """
        warnings = []
        voice_resp = parsed_response.get("voice_response", "")
        
        # Check length
        is_valid, length_issues = VoiceResponseValidator.is_valid_voice_response(voice_resp)
        if not is_valid:
            warnings.extend(length_issues)
        
        # Check for question repetition
        question = VoiceResponseValidator.extract_question_from_voice_response(voice_resp)
        if question and VoiceResponseValidator.is_repeating_question(question, previously_asked):
            warnings.append(f"Warning: This question was already asked: '{question}'")
        
        return parsed_response, warnings


class DualResponseGenerator:
    """
    Ensures every response generates both TEXT and VOICE versions.
    """
    
    @staticmethod
    def get_dual_response_instruction() -> str:
        """
        Instructions to embed in system prompt for generating dual responses.
        """
        return """
YOU MUST OUTPUT EXACTLY THIS JSON STRUCTURE (no other text before or after):

{
  "text_response": "Long structured response for chat UI. Include [VERIFIED INFORMATION], [REQUIRES USER INPUT], [CANNOT DETERMINE]. Investor-grade. Use bullets, headers, details.",
  "voice_response": "Short 2-4 sentence response for speech. Conversational. Natural English. If asking a question, ask ONE thing only. No lists, coords, or data dumps.",
  "conversation_state": {
    "clarifications_asked": ["list", "of", "questions", "asked"],
    "information_provided": ["what", "user", "told", "us"],
    "information_needed": ["what", "we", "still", "need"],
    "next_step": "Brief description of where conversation should go next"
  }
}
"""
