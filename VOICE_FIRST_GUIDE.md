# Voice-First Conversational AI: Implementation Guide

## Overview

This document explains the transformation of the MP Industrial FastAPI system from text-first to voice-first, with natural, multi-turn conversational capabilities.

## Key Architecture Changes

### 1. **Dual Response Generation** (NEW)

Every response the LLM generates now produces **TWO versions**:

```
SINGLE LLM CALL
    ↓
TEXT RESPONSE (for Chat UI)
│ • Long (500+ words)
│ • Structured with sections
│ • [VERIFIED INFORMATION]
│ • [REQUIRES USER INPUT]
│ • [CANNOT DETERMINE]
│ • Investor-grade detail
│
VOICE RESPONSE (for TTS)
  • Short (2-4 sentences)
  • Conversational tone
  • One question at a time
  • No lists/data dumps
  • Sounds human
```

**Why?** The same information serves two different contexts:
- Chat users want detail and structure
- Voice users want brevity and natural flow

### 2. **Conversation State Tracking** (NEW)

The system now maintains state across multiple turns:

```python
voiceConversationState = {
    "conversation_history": [
        {
            "user_input": "What parks are near Indore?",
            "voice_response": "We have 3 parks near Indore...",
            "text_response": "[VERIFIED INFORMATION]..."
        }
    ],
    "previously_asked": [
        "Which district are you interested in?",
        "What's your budget?"
    ],
    "provided_info": {
        "district": "Indore",
        "industry": "Pharma"
    },
    "missing_info": ["budget", "plot_size"],
    "turn_number": 2
}
```

**What this enables:**
- ✅ AI remembers what user already said
- ✅ AI doesn't repeat questions
- ✅ AI builds follow-ups naturally
- ✅ AI asks one thing at a time

## File Changes

### New Files Created

#### 1. `app/agents/voice_prompts.py`
Conversational prompt engineering for voice mode.

**Key Classes:**
- `VoicePromptEngine`: Generates voice-optimized prompts
- `ConversationStateTracker`: Tracks multi-turn context

**Key Methods:**
```python
# System prompt enforcing natural voice behavior
VoicePromptEngine.get_voice_system_prompt()

# User prompt with conversation history
VoicePromptEngine.get_voice_user_prompt(
    question, 
    retrieved_data, 
    conversation_history,
    previous_clarifications
)

# Track state across turns
tracker = ConversationStateTracker("conversation_id")
tracker.add_turn(user_input, voice_response, text_response)
context = tracker.get_conversation_context()
```

#### 2. `app/agents/voice_validator.py`
Quality checks for voice responses.

**Key Classes:**
- `VoiceResponseValidator`: Enforces conversational standards
- `DualResponseGenerator`: Ensures both response types are generated

**Key Methods:**
```python
# Check if response is too long/monologue-like
is_valid, issues = VoiceResponseValidator.is_valid_voice_response(voice_response)

# Parse LLM JSON response
success, parsed, error = VoiceResponseValidator.parse_dual_response(llm_output)

# Check if question was already asked
is_repeating = VoiceResponseValidator.is_repeating_question(
    new_question, 
    previously_asked
)

# Validate and warn about issues
validated, warnings = VoiceResponseValidator.validate_and_fix_voice_response(
    parsed_response,
    previously_asked
)
```

### Modified Files

#### 1. `app/services/llm_factory.py`

**New Method:**
```python
@staticmethod
def generate_dual_response(
    question: str,
    context_data: Dict[str, Any],
    conversation_context: Dict[str, Any] = None
) -> Dict[str, Any]
```

**What it does:**
1. Builds voice-optimized prompts with history
2. Calls LLM once to generate BOTH responses
3. Validates voice response is conversational
4. Returns structured response

**Usage:**
```python
response = llm.generate_dual_response(
    question="Are there parks near Indore?",
    context_data={
        "policies": [...],
        "parks": [...],
        "plots": [...]
    },
    conversation_context=voiceConversationState
)

# Returns:
{
    "status": "success",
    "text_response": "...",  # Long, structured
    "voice_response": "...",  # Short, conversational
    "conversation_state": {...},  # Updated state
    "model": "gpt-4o",
    "warnings": []
}
```

#### 2. `app/main.py` - `/api/ask/voice` Endpoint

**Before:**
```python
@app.post("/api/ask/voice")
def ask_with_voice(payload: dict):
    # 1. Generate detailed response
    # 2. Summarize for voice (separate call)
    # 3. Convert to audio
```

**After:**
```python
@app.post("/api/ask/voice")
def ask_with_voice(payload: dict):
    # Payload includes:
    # - question: str
    # - conversation_state: dict  ← NEW!
    # - state: str
    
    # 1. Retrieve tools data
    # 2. Generate DUAL responses (single LLM call)
    # 3. Update conversation state
    # 4. Convert voice response to audio
    # 5. Return both responses + updated state
```

**New Response Structure:**
```json
{
    "text_response": "Long detailed response for chat UI...",
    "voice_response": "Short 2-4 sentence response for TTS...",
    "audio_base64": "base64-encoded MP3...",
    "conversation_state": {
        "conversation_history": [...],
        "previously_asked": [...],
        "provided_info": {...},
        "missing_info": [...],
        "turn_number": 2
    },
    "model": "gpt-4o",
    "provider": "openai",
    "turn_number": 2,
    "warnings": []
}
```

#### 3. `static/index.html` - Frontend

**New JavaScript State:**
```javascript
let voiceConversationState = {
    conversation_history: [],
    previously_asked: [],
    provided_info: {},
    missing_info: [],
    turn_number: 0,
};
```

**New Function:**
```javascript
// Reset conversation context between different topics
function resetVoiceConversation() {
    voiceConversationState = {...};
    console.log("Voice conversation reset");
}
```

**Updated `askAgentWithVoice()`:**
```javascript
async function askAgentWithVoice(questionText) {
    const payload = {
        question: questionText,
        state: document.getElementById("state").value,
        conversation_state: voiceConversationState  // ← Include state!
    };

    const data = await fetch('/api/ask/voice', {
        method: "POST",
        body: JSON.stringify(payload)
    });

    // Update state for next turn
    voiceConversationState = data.conversation_state;
    
    // Add to history
    voiceConversationState.conversation_history.push({
        user_input: questionText,
        voice_response: data.voice_response,
        text_response: data.text_response
    });
    
    // Display both text and voice
    renderBotResponse({ answer: data.text_response });
    playAudio(data.audio_base64);
}
```

**New UI Button:**
- Reset button (↻) to clear conversation state when starting new topic

## Behavior Changes

### Voice Mode (TTS) - BEFORE
❌ **Problems:**
- One-way monologue
- Answer everything in single response
- Can't ask follow-up questions
- Repeated same info if user asked again
- No sense of conversation

**Example:**
> "Madhya Pradesh has 15 industrial parks including Indore Industrial Park with area 2500 acres at coordinates 22.7196, 75.8577, established in 2005. You can also apply for plots in the following sections: Section A, Section B, Section C..."

---

### Voice Mode (TTS) - AFTER
✅ **Improvements:**
- Natural back-and-forth dialogue
- Short answers (2-4 sentences)
- Asks clarifying questions
- Remembers what was said
- Conversational, human-like

**Example:**
> Turn 1 (AI): "Madhya Pradesh has several industrial parks. Are you interested in a specific district like Indore or Bhopal?"
>
> Turn 2 (User): "Indore please"
>
> Turn 3 (AI): "Great! We have parks in Indore for pharma and automotive. What industry are you in?"
>
> Turn 4 (User): "Pharma"
>
> Turn 5 (AI): "Perfect. We have 3 pharma-approved parks there. What's your budget range?"

---

## How to Use

### For Users (Voice Interaction)

1. Click **🎤 Speak** button
2. Say your question naturally
3. AI asks clarifying questions
4. Continue speaking your answers
5. AI builds conversation context
6. Click **↻ Reset** to start new topic

### For Developers (API)

#### Example: Single Turn
```bash
curl -X POST http://localhost:8000/api/ask/voice \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me parks near Indore",
    "state": "madhya_pradesh"
  }'
```

#### Example: Multi-Turn Conversation
```javascript
// Turn 1: Initial question
const turn1Response = await fetch('/api/ask/voice', {
    method: 'POST',
    body: JSON.stringify({
        question: "What industrial parks are available?",
        state: "madhya_pradesh",
        // No conversation_state on first turn
    })
});

const turn1Data = await turn1Response.json();
// Now turn1Data.conversation_state is populated

// Turn 2: Follow-up with state
const turn2Response = await fetch('/api/ask/voice', {
    method: 'POST',
    body: JSON.stringify({
        question: "Indore please",
        state: "madhya_pradesh",
        conversation_state: turn1Data.conversation_state  // ← Pass it back!
    })
});

const turn2Data = await turn2Response.json();
// AI now remembers "parks" context and doesn't repeat questions
```

## Prompt Engineering Details

### Voice System Prompt (`voice_prompts.py`)

Key rules enforced:

1. **Two Internal Response Formats**
   - TEXT: Long, structured, investor-grade (for chat)
   - VOICE: Short, conversational, spoken English (for TTS)

2. **Question-Driven Conversation**
   - Ask ONE question at a time
   - Natural phrasing: "Which district interests you?" not "I require location"
   - Pause and wait for answer

3. **No Monologues**
   - Max 4 sentences
   - Avoid bullet points, lists, coordinates
   - Sound like a human consultant

4. **Context Awareness**
   - Remember previous turns in conversation
   - Don't repeat questions already answered
   - Build follow-ups naturally

5. **Fact Safety**
   - Never guess distances, prices, availability
   - If uncertain, ask for clarification
   - If not in data: "That's not in our system - what's your specific need?"

### Response Validation (`voice_validator.py`)

The system validates:
- ✅ Response length (max 60 words / 4 sentences)
- ✅ No bullet points, lists, or section headers
- ✅ Question not repeating previous ones
- ✅ JSON structure valid
- ✅ No technical data/coordinates

If validation fails, warnings are logged (response still sent, but flagged).

## Configuration

### Environment Variables

No new environment variables required. Uses existing:
- `LLM_PROVIDER` (groq/openai)
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (gpt-4o recommended)
- `GROQ_API_KEY`
- `GROQ_MODEL`
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`

### LLM Recommendations

**For best conversational results:**

| Provider | Model | Why |
|----------|-------|-----|
| OpenAI | `gpt-4o` | Best at understanding context and generating concise responses |
| Groq | `mixtral-8x7b-32768` | Fast, good for real-time voice |

**Temperature:** 0.6 (slightly creative, not too random)

**Max tokens:** 2000 (allows both text + voice response)

## Troubleshooting

### Issue: Voice responses are too long
**Solution:** Check voice prompt is being used. Verify `voice_response` field in LLM output is under 60 words.

### Issue: AI repeats the same question
**Solution:** Ensure `previous_clarifications` list is being passed from frontend state. Check browser console for `voiceConversationState`.

### Issue: Audio doesn't play
**Solution:** 
1. Check ElevenLabs API key is set
2. Check browser console for errors
3. Verify TTS synthesis in response contains valid base64

### Issue: Conversation state not persisting
**Solution:** Frontend must pass `conversation_state` in each request body. Check network tab to verify payload includes state object.

## Testing

### Test 1: Single-Turn Voice
```python
# Should return short, natural response
response = requests.post(
    "http://localhost:8000/api/ask/voice",
    json={"question": "What policies exist?", "state": "madhya_pradesh"}
)
assert response.json()["voice_response"]  # 2-4 sentences max
```

### Test 2: Multi-Turn Conversation
```python
# First turn
r1 = requests.post("http://localhost:8000/api/ask/voice",
    json={"question": "Show me parks"})
state1 = r1.json()["conversation_state"]

# Second turn with state
r2 = requests.post("http://localhost:8000/api/ask/voice",
    json={
        "question": "In Indore",
        "conversation_state": state1  # Pass it back
    }
)

# AI should NOT ask "Which district?" again
assert "district" not in r2.json()["voice_response"].lower()
```

### Test 3: Response Format
```python
response = requests.post("http://localhost:8000/api/ask/voice",
    json={"question": "..."})
data = response.json()

# Both responses should exist
assert "text_response" in data
assert "voice_response" in data
assert "conversation_state" in data

# Voice should be short
assert len(data["voice_response"].split()) < 70

# Text should be long
assert len(data["text_response"].split()) > 100
```

## FAQ

**Q: Why generate both TEXT and VOICE responses?**
A: Different mediums have different needs. Chat users want structured detail. Voice users want natural brevity. Same LLM call serves both efficiently.

**Q: Why track conversation state in frontend?**
A: Because the backend is stateless (REST API). The frontend maintains state and sends it back with each request. This enables multi-turn conversations without backend session storage.

**Q: Can users switch between text and voice mid-conversation?**
A: Currently, they're separate (text chat vs voice conversation). You could enhance by sharing state between them.

**Q: What if the user's question isn't answered?**
A: The AI will ask for clarification instead of guessing. This is intentional for fact safety.

**Q: How do I integrate this with my chatbot platform?**
A: The `/api/ask/voice` endpoint is a standard REST API. Pass `conversation_state` in request body to maintain context across turns.

---

## Next Steps

### Optional Enhancements

1. **Session Persistence**
   - Store conversation state in database
   - Enable multi-device access
   - Add conversation history UI

2. **Sentiment Analysis**
   - Track user satisfaction across turns
   - Adjust tone if user seems frustrated

3. **Intent Detection**
   - Explicitly categorize: clarification_needed, info_provided, decision_made
   - Route to specialist (sales, tech support, etc.)

4. **A/B Testing**
   - Test different voice tones
   - Measure engagement, completion rates
   - Optimize prompts based on metrics

5. **Multi-Language Support**
   - Hindi, Marathi, Gujarati support
   - Code-switching detection

---

**Last Updated:** January 22, 2026  
**Status:** Production Ready
