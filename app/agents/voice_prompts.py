"""
Voice-first prompt engineering for natural, conversational interactions.

This module enforces the dual-response pattern:
1. TEXT: Long, structured, investor-grade (for chat UI)
2. VOICE: Short, conversational, question-driven (for TTS)

The same LLM query generates both responses internally using structured prompts.
"""

from typing import Dict, Any, List, Optional


class VoicePromptEngine:
    """
    Generates prompts for conversational, multi-turn voice interactions.
    
    Key behaviors:
    - Asks one question at a time
    - Maintains short responses (2-4 sentences)
    - Tracks context to avoid repetition
    - Sounds like a human consultant
    """
    
    @staticmethod
    def get_voice_system_prompt() -> str:
        """
        System prompt for voice mode. Enforces natural, brief, question-driven responses.
        """
        return """You are a natural, conversational industrial policy advisor speaking with an investor.

CRITICAL VOICE BEHAVIORS:
1. SHORT RESPONSES ONLY (2-4 sentences max for voice)
2. ASK ONE QUESTION AT A TIME when you need info
3. SOUND HUMAN - no lists, no data dumps, no section headers
4. REMEMBER what the user already told you - don't repeat questions
5. Keep the conversation flowing back-and-forth, not one-way

RESPONSE STRUCTURE (INTERNAL ONLY, NOT VISIBLE TO USER):
You MUST output JSON with this exact structure:

{
  "text_response": "Long, structured response with [VERIFIED INFORMATION], [REQUIRES USER INPUT], [CANNOT DETERMINE] sections. Investor-grade. For chat UI only.",
  "voice_response": "Short 2-4 sentence response. Conversational. One question if needed. Spoken English. No bullets, no coords, no data dumps. For TTS.",
  "conversation_state": {
    "clarifications_asked": ["list of questions you've asked so far"],
    "information_provided": ["list of info user has given"],
    "information_needed": ["list of missing required info"],
    "next_step": "what you should ask or say next turn"
  }
}

VOICE RULES:
- Never say "According to policy..." - say "We can set that up in..."
- Never list items - say "Your top option would be..."
- Never give coordinates - say "It's centrally located..."
- Never say "I require 5 pieces of information" - ask "Which district interests you?"
- If uncertain about facts: "I'd need to verify that - what's your location?" (not "I cannot determine")

FACT SAFETY:
- NEVER guess distances, prices, or availability
- If you don't know, ask for clarification
- If it's not in the data, say "That's not in our system - let me know your needs"
"""

    @staticmethod
    def get_voice_user_prompt(
        question: str,
        retrieved_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        previous_clarifications: Optional[List[str]] = None,
    ) -> str:
        """
        Build user prompt for voice mode with context and conversation history.
        
        Args:
            question: User's current question
            retrieved_data: Retrieved policies, parks, plots, POIs
            conversation_history: Previous turns in this conversation
            previous_clarifications: Questions already asked (to avoid repeating)
        """
        
        prompt = "## CONVERSATION CONTEXT\n\n"
        
        # Add conversation history if present
        if conversation_history:
            prompt += "### Previous Turns:\n"
            for turn in conversation_history[-5:]:  # Last 5 turns only
                prompt += f"- User: {turn.get('user_input', '')}\n"
                prompt += f"- You (voice): {turn.get('voice_response', '')}\n\n"
            prompt += "\n"
        
        # Add what we've already asked (to prevent repetition)
        if previous_clarifications:
            prompt += f"### Already Asked: {', '.join(previous_clarifications)}\n"
            prompt += "**DO NOT repeat these questions.**\n\n"
        
        # Add available data
        prompt += "## AVAILABLE DATA FOR THIS QUERY\n\n"
        
        if retrieved_data.get("policies"):
            prompt += "### Relevant Policies:\n"
            for policy in retrieved_data["policies"][:3]:
                prompt += f"- {policy.get('source', 'Unknown')}: "
                prompt += f"{policy.get('text', '')[:150]}...\n"
        
        if retrieved_data.get("parks"):
            prompt += "\n### Industrial Parks Available:\n"
            for park in retrieved_data["parks"][:3]:
                prompt += f"- {park.get('park_name', 'Unknown')} "
                prompt += f"({park.get('district', '?')}): {park.get('status', 'Active')}\n"
        
        if retrieved_data.get("plots"):
            prompt += f"\n### Available Plots: {len(retrieved_data['plots'])} plots found\n"
        
        if retrieved_data.get("pois"):
            prompt += f"\n### Nearby Infrastructure: {len(retrieved_data.get('pois', []))} points found\n"
        
        prompt += f"\n## USER'S CURRENT QUESTION\n{question}\n\n"
        
        prompt += """## YOUR RESPONSE (JSON ONLY)

Output ONLY valid JSON in this format:
```json
{
  "text_response": "...",
  "voice_response": "...",
  "conversation_state": {
    "clarifications_asked": [...],
    "information_provided": [...],
    "information_needed": [...],
    "next_step": "..."
  }
}
```

Do not add any text before or after the JSON.
"""
        return prompt

    @staticmethod
    def get_single_question_prompt(
        user_input: str,
        question_to_ask: str,
    ) -> str:
        """
        Prompt for asking a clarifying question naturally.
        Used when you need more info before answering.
        """
        return f"""The user said: "{user_input}"

You need to clarify: {question_to_ask}

Generate a natural, conversational follow-up question to ask them (for voice).
Keep it to 1 sentence. Sound like a friendly consultant.
Format as JSON:

{{
  "voice_response": "Your question here",
  "next_step": "Waiting for user to answer"
}}
"""

    @staticmethod
    def get_response_formatter_prompt(
        detailed_answer: str,
        conversation_turn_number: int = 1,
    ) -> str:
        """
        Convert a detailed response into a natural voice summary.
        """
        turn_desc = (
            "first response - be welcoming" if conversation_turn_number == 1
            else "follow-up - be concise"
        )
        
        return f"""You have this detailed investor response:

{detailed_answer}

Convert it to a natural voice response ({turn_desc}).

RULES:
- 2-4 sentences max
- Conversational, no jargon
- If asking a follow-up, make it 1 clear question
- No bullet points, lists, or coordinates
- Sound like a human advisor

Output JSON:
{{
  "voice_response": "..."
}}
"""


class ConversationStateTracker:
    """
    Tracks conversation state across multiple voice turns.
    Prevents question repetition and maintains context.
    """
    
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.history: List[Dict[str, Any]] = []
        self.asked_questions: List[str] = []
        self.provided_info: Dict[str, Any] = {}
        self.missing_info: List[str] = []
    
    def add_turn(
        self,
        user_input: str,
        voice_response: str,
        text_response: str,
        clarifications_asked: Optional[List[str]] = None,
    ) -> None:
        """Record a conversation turn."""
        self.history.append({
            "turn_number": len(self.history) + 1,
            "user_input": user_input,
            "voice_response": voice_response,
            "text_response": text_response,
            "timestamp": None,  # Add if needed
        })
        
        if clarifications_asked:
            self.asked_questions.extend(clarifications_asked)
    
    def get_conversation_context(self) -> Dict[str, Any]:
        """Return context for the next LLM call."""
        return {
            "conversation_history": self.history,
            "previously_asked": self.asked_questions,
            "provided_info": self.provided_info,
            "missing_info": self.missing_info,
            "turn_number": len(self.history) + 1,
        }
    
    def should_ask_question(self, missing_fields: List[str]) -> bool:
        """Determine if we should ask for clarification."""
        # Don't ask if we've already asked for this info
        already_asked = any(field.lower() in q.lower() for field in missing_fields for q in self.asked_questions)
        return not already_asked and len(missing_fields) > 0
    
    def get_unanswered_questions(self) -> List[str]:
        """Get list of questions we haven't received answers for."""
        # In a real implementation, analyze conversation_history to see which questions went unanswered
        return self.asked_questions[len(self.history):]
