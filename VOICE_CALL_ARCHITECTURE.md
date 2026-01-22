# 🏗️ Voice Call Agent - Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  static/call.html - Call Interface                              │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ Call Status     │ Listening... 👂                         │ │ │
│  │  │ Conversation:   │ Agent: "Hello, how can I help?"         │ │ │
│  │  │                 │ You: "I need pharma opportunities"      │ │ │
│  │  │ Controls:       │ [Start Call] [End Call]                │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │ JavaScript Engine                                          │ │ │
│  │  │ ├─ State Machine (IDLE→AGENT→USER→LISTENING→REPEAT)      │ │ │
│  │  │ ├─ Web Speech API (speech recognition)                    │ │ │
│  │  │ ├─ Audio Playback (HTML5 Audio)                          │ │ │
│  │  │ └─ Session Management (call ID tracking)                  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  Microphone Input ──────────────────────────────────────────────────────│
│  Speaker Output ───────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
                            HTTP/JSON APIs
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                       FASTAPI BACKEND                                   │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ POST /api/call/start                                           │ │
│  │ ├─ Generate greeting                                          │ │
│  │ ├─ Create session (UUID)                                      │ │
│  │ ├─ Synthesize TTS                                            │ │
│  │ └─ Return: call_id, audio_base64, greeting                  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ POST /api/call/send                                          │ │
│  │ ├─ Receive user message                                      │ │
│  │ ├─ Update conversation history                               │ │
│  │ ├─ Call run_agent(state, message, context)                  │ │
│  │ ├─ Generate voice_response (short)                          │ │
│  │ ├─ Synthesize TTS for voice_response                        │ │
│  │ ├─ Extract investor context                                  │ │
│  │ └─ Return: agent_response, audio_base64, state              │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ POST /api/call/end                                           │ │
│  │ ├─ Retrieve full conversation history                        │ │
│  │ ├─ Generate summary                                          │ │
│  │ ├─ Synthesize summary TTS                                   │ │
│  │ └─ Return: summary, audio_base64, metadata                  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Call Session Store (In-Memory)                               │ │
│  │ {                                                             │ │
│  │   "call_id": {...},                                          │ │
│  │   "conversation_history": [...],                            │ │
│  │   "investor_preferences": {...},                            │ │
│  │   "state": "madhya_pradesh"                                 │ │
│  │ }                                                             │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
                         Call Agent Module
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                       AGENT ENGINE                                      │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ run_agent(state, question, context, is_voice_mode=True)        │ │
│  │ ├─ Validate input                                              │ │
│  │ ├─ Execute tools intelligently                                │ │
│  │ │  ├─ search_policy() - Policy retrieval                    │ │
│  │ │  ├─ get_parks() - Park data                               │ │
│  │ │  └─ get_plots() - Plot data                               │ │
│  │ ├─ Generate response with LLM                                │ │
│  │ │  ├─ System Prompt: _get_voice_system_prompt()           │ │
│  │ │  ├─ Context: Retrieved data + conversation history       │ │
│  │ │  └─ User Query: Current question                         │ │
│  │ ├─ Validate response (hallucination check)                 │ │
│  │ ├─ Create voice_response (short, conversational)           │ │
│  │ └─ Return: {voice_response, text_response, state}          │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
                         External Services
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                                    │
│  ┌─────────────────────┐      ┌─────────────────────┐                 │
│  │   ElevenLabs TTS    │      │   LLM Service       │                 │
│  │ (Audio Synthesis)   │      │ (Groq/OpenAI)       │                 │
│  │                     │      │                     │                 │
│  │ Text → MP3 Audio    │      │ Prompt → Response   │                 │
│  │ (128 kbps mono)     │      │ (Mixtral/GPT-4)     │                 │
│  └─────────────────────┘      └─────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow - Call Lifecycle

### 1. Call Initiation
```
User clicks "Start Call"
    ↓
Frontend → POST /api/call/start
    ↓
Backend generates greeting
    ↓
Synthesize greeting → ElevenLabs TTS
    ↓
Return: {call_id, audio_base64, voice_state: "AGENT_SPEAKING"}
    ↓
Frontend plays audio
    ↓
Frontend sets state to "LISTENING" after audio ends
    ↓
Microphone activates for user input
```

### 2. Message Exchange
```
User speaks
    ↓
Frontend → Web Speech API
    ↓
Transcription: "I'm interested in pharmaceuticals"
    ↓
Frontend sets state to "AGENT_SPEAKING"
    ↓
Frontend → POST /api/call/send {call_id, user_message}
    ↓
Backend saves message to conversation history
    ↓
Backend calls run_agent() with voice_mode=True
    ↓
run_agent():
  ├─ Retrieves relevant data (search_policy, get_parks)
  ├─ Calls LLM with voice system prompt + context
  ├─ Generates detailed response
  └─ Creates short voice_response via _create_voice_response()
    ↓
Backend synthesizes voice_response → ElevenLabs
    ↓
Returns: {agent_response, audio_base64, conversation_state}
    ↓
Frontend plays audio
    ↓
Frontend updates investor preferences from conversation_state
    ↓
Frontend sets state to "LISTENING" after audio
    ↓
(Loop: Mic activates for next input)
```

### 3. Call Termination
```
User clicks "End Call"
    ↓
Frontend → POST /api/call/end {call_id}
    ↓
Backend retrieves full conversation history
    ↓
Backend generates summary:
  ├─ Extract investor intent
  ├─ Identify sector/location preferences
  ├─ Count opportunities discussed
  └─ Suggest next steps
    ↓
Backend creates summary_text (human-readable)
    ↓
Backend synthesizes summary_text → ElevenLabs TTS
    ↓
Returns: {summary, summary_audio, duration_seconds}
    ↓
Frontend plays summary audio
    ↓
Frontend displays summary card with details
    ↓
User can start new call or close
```

---

## Response Format Details

### API Response Structure (Unified Format)

```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  
  "voice_response": "Great! We have excellent opportunities in pharmaceuticals...",
  "text_response": "[VERIFIED INFORMATION] Pipariya Park...",
  "audio_base64": "//NExAAR7RQAHgAAQAIACa1A...",
  
  "voice_state": "AGENT_SPEAKING",
  "turn_count": 3,
  
  "conversation_state": {
    "investor_sector": "Pharmaceuticals",
    "investor_location": "Indore",
    "turn_count": 3
  },
  
  "metadata": {
    "duration_ms": 2100,
    "audio_size_kb": 45.2
  }
}
```

### Response Routing

| Field | Purpose | Used By |
|-------|---------|---------|
| `voice_response` | Short, conversational (2-4 sentences) | TTS input + display label |
| `text_response` | Detailed, structured with tags | Display/reference (if shown) |
| `audio_base64` | MP3 audio for playback | HTML5 Audio API |
| `voice_state` | Current state machine state | Frontend state management |
| `turn_count` | Conversation progress | UI display + context |
| `conversation_state` | Updated preferences | Context for next message |

---

## State Transitions (Frontend)

```
                    ┌─────────────────┐
                    │   User Page     │
                    │   Load (IDLE)   │
                    └────────┬────────┘
                             │
                    [Start Call Click]
                             │
                             ↓
                    ┌─────────────────────┐
                    │   AGENT_SPEAKING    │
                    │  Playing greeting   │
                    └────────┬────────────┘
                             │
                   [Greeting ends / Timer]
                             │
                             ↓
                    ┌─────────────────────┐
                    │   LISTENING         │
                    │ Mic activated       │
                    │ Audio wave showing  │
                    └────────┬────────────┘
                             │
               [User speaking / Recognition starts]
                             │
                             ↓
                    ┌─────────────────────┐
                    │   USER_SPEAKING     │
                    │  Transcribing       │
                    └────────┬────────────┘
                             │
                  [Transcript → Send to Agent]
                             │
                             ↓
                    ┌─────────────────────┐
                    │   AGENT_SPEAKING    │
                    │  Response playing   │
                    └────────┬────────────┘
                             │
                   [Response ends / Timer]
                             │
         ┌───────────────────┴───────────────────┐
         │                                       │
    [End Call]                                   
         │                              [Continue]
         │                                       │
         ↓                                       ↓
  ┌─────────────────┐            ┌───────────────────────┐
  │  Generate       │            │  Loop back to         │
  │  Summary        │            │  LISTENING state      │
  │  Audio plays    │            └───────────────────────┘
  │                 │
  │  IDLE           │
  └─────────────────┘
```

---

## Component Interaction Matrix

| Frontend | ↔ Backend | ↔ LLM | ↔ TTS | ↔ Browser |
|----------|-----------|-------|-------|-----------|
| HTML UI | Call API | run_agent() | ElevenLabs | DOM Updates |
| State Machine | Session Manager | Prompt Template | Synthesis | Status Display |
| Speech Recognition | Conversation Store | Tool Execution | Audio Encoding | Audio Playback |
| Audio Playback | Investor Tracker | Response Validation | MP3 Encoding | Microphone |
| Message Display | Context Extractor | Voice Prompt | Base64 Encode | Event Listeners |

---

## Error Handling Flow

```
Request → Backend
    ├─ Validation
    │  ├─ Invalid call_id → Return error
    │  ├─ Invalid state → Return error
    │  └─ Empty message → Return error
    │
    ├─ Agent Processing
    │  ├─ Tool error → Graceful fallback
    │  ├─ LLM timeout → Generic response
    │  └─ Response validation fail → Regenerate
    │
    ├─ TTS Processing
    │  ├─ API key missing → Log warning, return None
    │  ├─ API error → Return response without audio
    │  └─ Invalid text → Truncate safely
    │
    └─ Return Response
       ├─ With audio (success case)
       └─ Without audio (graceful fallback)

Frontend → Catches error
    ├─ Display error message
    ├─ Offer retry
    └─ Keep call active
```

---

## Call Session Lifecycle (Backend)

```
Session Created (Start Call)
    ├─ UUID generated
    ├─ Timestamp recorded
    ├─ Initial state: "active"
    └─ Empty conversation_history

During Call (Send Messages)
    ├─ Each message appended to history
    ├─ turn_count incremented
    ├─ Context extracted and stored
    └─ Preferences updated

On End Call
    ├─ Status: "ended"
    ├─ Ended_at: timestamp
    ├─ Summary generated
    ├─ Duration calculated
    └─ Session marked for cleanup
```

---

## Scalability Considerations

### Current Implementation (In-Memory)
```
Limitations:
- Single server instance only
- Sessions lost on restart
- Max ~1000 concurrent calls
```

### Production Upgrade Path
```
Option 1: Redis Session Store
  Session Store → Redis
  Allows horizontal scaling
  Persistent across restarts

Option 2: Database (PostgreSQL)
  Full persistence
  Analytics queries
  Audit logging
  Multi-region support
```

---

## Performance Optimization Opportunities

| Area | Current | Optimized |
|------|---------|-----------|
| **Response Time** | 1-2s | Pre-cache common greetings |
| **Audio Encoding** | On-demand | Pre-encode with caching |
| **Tool Calls** | Parallel | Add batching |
| **LLM Calls** | Sequential | Implement queue/priority |
| **Session Cleanup** | Manual | Background worker |

---

## Deployment Architecture

```
Production Setup:

Load Balancer (Nginx)
    ↓
Kubernetes Pods (FastAPI)
    ├─ Pod 1 (app.main)
    ├─ Pod 2 (app.main)
    └─ Pod 3 (app.main)
    ↓
Redis (Session Store)
    ↓
PostgreSQL (Persistent Store)
    ↓
External Services
    ├─ ElevenLabs (TTS)
    ├─ Groq/OpenAI (LLM)
    └─ Logging (CloudWatch/Datadog)
```

---

**Last Updated**: January 22, 2026  
**Status**: ✅ Production Ready Architecture
