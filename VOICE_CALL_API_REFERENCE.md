# 📡 Voice Call API Reference

## Base URL
```
http://localhost:8111
```

## Endpoints

### 1. Start Call

**Endpoint:** `POST /api/call/start`

**Purpose:** Initiates a new call session with agent greeting

**Request:**
```json
{
  "state": "madhya_pradesh",
  "investor_sector": "Pharmaceuticals",
  "investor_location": "Indore"
}
```

**Request Parameters:**
- `state` (string, required) - `"madhya_pradesh"` or `"maharashtra"`
- `investor_sector` (string, optional) - e.g., "Pharmaceuticals", "Automotive"
- `investor_location` (string, optional) - e.g., "Indore", "Bhopal", "Pune"

**Response (200 OK):**
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_greeting": "Hi there! I'm your industrial investment advisor...",
  "audio_base64": "//NExAAR7RQAHgAAQAIACa1A...",
  "voice_state": "AGENT_SPEAKING",
  "turn_count": 0
}
```

**Response Fields:**
- `call_id` - Session ID for subsequent calls (save this!)
- `agent_greeting` - Text of the greeting
- `audio_base64` - MP3 audio encoded as base64
- `voice_state` - Current state ("AGENT_SPEAKING")
- `turn_count` - Current turn number (starts at 0)

**Example (JavaScript):**
```javascript
const response = await fetch('http://localhost:8111/api/call/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    state: 'madhya_pradesh',
    investor_sector: 'Pharmaceuticals'
  })
});

const data = await response.json();
const callId = data.call_id;

// Play audio
const audio = new Audio('data:audio/mpeg;base64,' + data.audio_base64);
await audio.play();
```

**Example (cURL):**
```bash
curl -X POST http://localhost:8111/api/call/start \
  -H "Content-Type: application/json" \
  -d '{
    "state": "madhya_pradesh",
    "investor_sector": "Pharmaceuticals"
  }'
```

---

### 2. Send Message

**Endpoint:** `POST /api/call/send`

**Purpose:** Send user message, receive agent response

**Request:**
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_message": "I'm interested in pharmaceutical manufacturing with a 12-month timeline"
}
```

**Request Parameters:**
- `call_id` (string, required) - From `/api/call/start` response
- `user_message` (string, required) - User's spoken/typed input

**Response (200 OK):**
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_response": "Great! We have excellent pharmaceutical manufacturing parks in Indore...",
  "text_response": "[VERIFIED INFORMATION] Pipariya Park: 2,000 acres...",
  "audio_base64": "//NExAAR7RQAHgAAQAIACa1A...",
  "voice_state": "AGENT_SPEAKING",
  "turn_count": 2,
  "conversation_state": {
    "investor_sector": "Pharmaceuticals",
    "investor_location": "Indore",
    "turn_count": 2
  }
}
```

**Response Fields:**
- `agent_response` - Natural conversational response (2-4 sentences)
- `text_response` - Structured response with details and citations
- `audio_base64` - MP3 audio of agent_response
- `voice_state` - Always "AGENT_SPEAKING" after response
- `conversation_state` - Updated investor preferences
- `turn_count` - Incremented conversation turn

**Key Difference:**
- `agent_response` - For voice playback (short, natural)
- `text_response` - For display/reference (detailed, structured)

**Example (JavaScript):**
```javascript
const response = await fetch('http://localhost:8111/api/call/send', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    call_id: callId,
    user_message: "I'm interested in pharmaceuticals"
  })
});

const data = await response.json();

// Play agent response audio
const audio = new Audio('data:audio/mpeg;base64,' + data.audio_base64);
await audio.play();

// Update context with conversation state
console.log('Updated preferences:', data.conversation_state);
```

**Example (Python):**
```python
import requests
import base64

call_id = "550e8400-e29b-41d4-a716-446655440000"

response = requests.post(
    'http://localhost:8111/api/call/send',
    json={
        'call_id': call_id,
        'user_message': 'What about logistics and connectivity?'
    }
)

data = response.json()
print("Agent said:", data['agent_response'])

# Decode and save audio if needed
audio_bytes = base64.b64decode(data['audio_base64'])
with open('response.mp3', 'wb') as f:
    f.write(audio_bytes)
```

---

### 3. End Call

**Endpoint:** `POST /api/call/end`

**Purpose:** Terminate call and generate summary

**Request:**
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Request Parameters:**
- `call_id` (string, required) - Session ID from start/send calls

**Response (200 OK):**
```json
{
  "call_id": "550e8400-e29b-41d4-a716-446655440000",
  "summary": {
    "investor_intent": "Exploring pharmaceutical manufacturing in Madhya Pradesh with 12-month timeline",
    "preferred_sector": "Pharmaceuticals",
    "preferred_location": "Indore",
    "opportunities_discussed": 3,
    "suggested_next_steps": [
      "Review detailed park/plot data",
      "Schedule site visit",
      "Connect with local authorities",
      "Finalize investment timeline"
    ]
  },
  "summary_text": "Thank you for taking the time to speak with us today...",
  "summary_audio": "//NExAAR7RQAHgAAQAIACa1A...",
  "turn_count": 6,
  "duration_seconds": 240
}
```

**Response Fields:**
- `summary` - Structured summary with investor intent and next steps
- `summary_text` - Spoken summary (human-readable text)
- `summary_audio` - MP3 of the spoken summary
- `turn_count` - Total number of conversation turns
- `duration_seconds` - Call duration in seconds

**Example (JavaScript):**
```javascript
const response = await fetch('http://localhost:8111/api/call/end', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    call_id: callId
  })
});

const data = await response.json();

// Play summary audio
const audio = new Audio('data:audio/mpeg;base64,' + data.summary_audio);
await audio.play();

// Display summary
console.log('Call Summary:');
console.log('Duration:', data.duration_seconds, 'seconds');
console.log('Investor Intent:', data.summary.investor_intent);
console.log('Next Steps:', data.summary.suggested_next_steps);
```

---

## Complete Example Flow

```javascript
// 1. START CALL
const startRes = await fetch('/api/call/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    state: 'madhya_pradesh',
    investor_sector: 'Pharmaceuticals'
  })
});

const startData = await startRes.json();
const callId = startData.call_id;

console.log('Agent:', startData.agent_greeting);
playAudio(startData.audio_base64);

// Wait for user input (speech recognition)
const userMessage = "I'm interested in pharmaceutical manufacturing";

// 2. SEND MESSAGE
const sendRes = await fetch('/api/call/send', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    call_id: callId,
    user_message: userMessage
  })
});

const sendData = await sendRes.json();
console.log('Agent:', sendData.agent_response);
playAudio(sendData.audio_base64);

// Repeat send/receive as needed...

// 3. END CALL
const endRes = await fetch('/api/call/end', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    call_id: callId
  })
});

const endData = await endRes.json();
console.log('Summary:', endData.summary);
playAudio(endData.summary_audio);
```

---

## Error Handling

### Invalid State
```json
{
  "error": "Invalid state. Available states: madhya_pradesh, maharashtra",
  "voice_state": "IDLE"
}
```

### Call Not Active
```json
{
  "error": "Call is not active",
  "voice_state": "IDLE"
}
```

### Server Error
```json
{
  "error": "Failed to process request",
  "call_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Rate Limits

- No explicit rate limits currently
- Reasonable per-call limits apply:
  - Max 100 turns per call
  - Max 5000 characters per message
  - Max 30 minute call duration

---

## Audio Format

- **Codec**: MP3
- **Bitrate**: 128 kbps
- **Sample Rate**: 24 kHz
- **Channels**: Mono
- **Encoding**: Base64 (for HTTP transmission)

---

## Integration Tips

### 1. **Handle Network Delays**
```javascript
const MAX_WAIT = 10000; // 10 seconds
const timeoutPromise = new Promise((_, reject) =>
  setTimeout(() => reject(new Error('Timeout')), MAX_WAIT)
);

try {
  await Promise.race([fetchPromise, timeoutPromise]);
} catch (e) {
  console.error('Request timeout or failed');
}
```

### 2. **Graceful Audio Fallback**
```javascript
async function playAudioSafely(base64) {
  try {
    const audio = new Audio('data:audio/mpeg;base64,' + base64);
    await audio.play();
  } catch (e) {
    console.warn('Audio playback failed:', e);
    // User can still see transcript
  }
}
```

### 3. **Persist Call Context**
```javascript
// Save call_id to localStorage for recovery
localStorage.setItem('current_call_id', callId);

// Recover if page reloads
const savedCallId = localStorage.getItem('current_call_id');
```

### 4. **Analytics Tracking**
```javascript
const callMetrics = {
  startTime: Date.now(),
  turnCount: data.turn_count,
  investorSector: data.conversation_state.investor_sector,
  callDuration: data.duration_seconds
};

// Send to analytics service
trackCall(callMetrics);
```

---

## Testing with Postman

1. **Collection**: Import as raw JSON
2. **Variables**: Set `{{base_url}}` = `http://localhost:8111`
3. **Environment**: Add `{{call_id}}` variable

```json
{
  "info": {
    "name": "Voice Call API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Start Call",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/call/start",
        "body": {
          "mode": "raw",
          "raw": "{\"state\": \"madhya_pradesh\"}"
        }
      }
    }
  ]
}
```

---

**Last Updated**: January 22, 2026  
**Status**: ✅ Production Ready
