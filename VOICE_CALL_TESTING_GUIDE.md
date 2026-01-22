# 🧪 Voice Call Agent - Testing & Validation Guide

## Pre-Launch Testing Checklist

### 1. Environment Setup ✅

- [ ] Python 3.9+ installed
- [ ] Virtual environment activated
- [ ] Requirements installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured with API keys:
  - [ ] `ELEVENLABS_API_KEY` set
  - [ ] `ELEVENLABS_VOICE_ID` set
  - [ ] `LLM_PROVIDER` set to `groq` or `openai`
  - [ ] `GROQ_API_KEY` or `OPENAI_API_KEY` set

### 2. Server Startup ✅

```bash
# Terminal 1: Start server
cd d:\Atharva\agentic-ai\mp-industrial-fastapi
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8111 --reload
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8111
INFO:     Application startup complete
```

- [ ] Server starts without errors
- [ ] No import errors
- [ ] Logger initialized
- [ ] Health check passes: `http://localhost:8111/api/health`

### 3. Frontend Access ✅

- [ ] Navigate to `http://localhost:8111/static/call.html`
- [ ] Page loads without console errors (F12)
- [ ] All UI elements visible:
  - [ ] State selector dropdown
  - [ ] Sector input field
  - [ ] Location input field
  - [ ] "Start Call" button
  - [ ] Call status indicator
  - [ ] Conversation area

---

## Functional Testing

### Test 1: Basic Call Start

**Steps:**
1. Open `http://localhost:8111/static/call.html`
2. Leave state as "Madhya Pradesh"
3. Click "▶️ Start Call"

**Expected:**
- [ ] Status changes to "Agent speaking..."
- [ ] Greeting displays in conversation
- [ ] Audio plays automatically (if TTS enabled)
- [ ] Unique `call_id` returned
- [ ] Status changes to "Listening..." after ~3 seconds

**Validation:**
```javascript
// Open DevTools (F12) → Console
// Check log output:
[CALL] Starting call with state = madhya_pradesh
[VOICE] Restarting recognition...
[STATE] Changed to: LISTENING
```

---

### Test 2: User Speech & Agent Response

**Steps:**
1. When status shows "👂 Listening..."
2. Click microphone and speak clearly:
   ```
   "I'm interested in pharmaceutical manufacturing"
   ```
3. Release microphone

**Expected:**
- [ ] Microphone indicator shows
- [ ] Speech recognized (appears in transcript)
- [ ] Status changes to "Agent speaking..."
- [ ] Agent response plays
- [ ] Response is conversational (not robotic)
- [ ] No [BRACKETS] visible
- [ ] 2-4 sentences maximum

**Example Response:**
```
"Great! We have excellent pharmaceutical 
manufacturing parks in Madhya Pradesh. 
Pipariya is particularly well-suited for 
your needs. What's your investment timeline?"
```

**Validation:**
```javascript
// DevTools Console:
[VOICE] User said: I'm interested in pharmaceutical manufacturing
[CALL] Turn 1: Agent responded
[STATE] Changed to: AGENT_SPEAKING
```

---

### Test 3: Multi-Turn Conversation

**Test Sequence:**

| Turn | You Say | Agent Should Ask |
|------|---------|------------------|
| 1 | "Pharma manufacturing in MP" | About timeline/budget |
| 2 | "12-month timeline, ₹50 crore budget" | About specific location |
| 3 | "Prefer Indore or Bhopal" | Infrastructure needs? |
| 4 | "Need good connectivity" | Confirm understanding |

**Expected:**
- [ ] Each turn completes without manual intervention
- [ ] Microphone auto-restarts between turns
- [ ] Conversation flows naturally
- [ ] Agent remembers previous answers (doesn't repeat)
- [ ] Status indicator pulses correctly
- [ ] Conversation area auto-scrolls

---

### Test 4: Call End & Summary

**Steps:**
1. After 4-5 turns of conversation
2. Click "⏹ End Call"

**Expected:**
- [ ] Status changes to idle
- [ ] Summary audio plays
- [ ] Summary card displays with:
  - [ ] Investor Intent
  - [ ] Preferred Sector
  - [ ] Preferred Location
  - [ ] Suggested Next Steps (as list)
- [ ] "Start New Call" button appears
- [ ] Can start another call

**Expected Summary:**
```
SUMMARY CARD
✅ Call Summary

Investor Intent: Exploring pharmaceutical manufacturing 
                 in Madhya Pradesh with ₹50 crore budget

Preferred Sector: Pharmaceuticals
Preferred Location: Indore or Bhopal

Suggested Next Steps:
• Review detailed park/plot data
• Schedule site visit
• Connect with local authorities
• Finalize investment timeline
```

---

## Quality Testing

### Voice Quality (Listening Test)

1. Start a call
2. Listen to agent greeting
3. Evaluate for:

- [ ] **Clarity**: Words are distinct, not slurred
- [ ] **Pace**: Not too fast, not too slow
- [ ] **Tone**: Professional but friendly
- [ ] **Naturalness**: Sounds human-like, not robotic
- [ ] **Pauses**: Natural pauses between sentences
- [ ] **No Artifacts**: No background noise or glitches

**Acceptable**: Natural sounding, clear pronunciation  
**Not Acceptable**: Robotic, unclear, background noise

---

### Responsiveness Quality

1. Multiple conversation turns
2. Evaluate for:

- [ ] **Relevance**: Answers address your question
- [ ] **Accuracy**: Information is correct
- [ ] **Brevity**: No unnecessary details
- [ ] **Follow-up**: Asks appropriate next question
- [ ] **Memory**: Recalls previous answers
- [ ] **Professionalism**: Maintains investor-like tone

**Example Good Response:**
```
"Perfect. The Indore parks have excellent rail 
connectivity and are 15 minutes from the airport. 
We can arrange a site visit next week if you'd like?"
```

**Example Bad Response (Now Fixed):**
```
"According to policy data [VERIFIED INFORMATION], 
rail connectivity infrastructure exists at these 
coordinates. [REQUIRES USER INPUT] Site visit date needed."
```

---

### Microphone & Speech Recognition

1. Speak at normal conversational pace
2. Use clear English pronunciation
3. Test with varying volumes:
   - [ ] Quiet voice (still recognized?)
   - [ ] Normal voice (works consistently?)
   - [ ] Loud voice (doesn't over-saturate?)
4. Test with background noise:
   - [ ] Slight background (still works?)
   - [ ] Moderate noise (degrades gracefully?)

---

## Browser Compatibility Testing

### Chrome (Primary)
```bash
# Launch with flags for testing
chrome --disable-background-networking \
       --disable-breakpad \
       --disable-client-side-phishing-detection \
       --disable-component-extensions
```

- [ ] Page loads
- [ ] All features work
- [ ] Audio plays
- [ ] Speech recognition works

### Edge
- [ ] Page loads
- [ ] Features work
- [ ] Audio plays
- [ ] Speech recognition works

### Firefox
- [ ] Page loads
- [ ] Features work (Firefox has limited Web Speech API)
- [ ] Audio plays
- [ ] Graceful degradation if speech not supported

### Mobile (iOS/Android)
- [ ] Layout responsive
- [ ] Buttons clickable
- [ ] Audio works
- [ ] Speech recognition available (browser-dependent)

---

## Error Handling Testing

### Test 1: Network Timeout
- [ ] Simulate slow network (DevTools throttling)
- [ ] Agent should still respond (within 10s timeout)
- [ ] No crash or freeze

### Test 2: Missing API Key
1. Remove `ELEVENLABS_API_KEY` from `.env`
2. Start call
3. Expected: No audio, but conversation continues with text

### Test 3: Invalid State
```bash
# Test with invalid state
POST /api/call/start
{
  "state": "invalid_state"
}
```

Expected Response:
```json
{
  "error": "Invalid state. Available states: madhya_pradesh, maharashtra"
}
```

### Test 4: Microphone Denied
- [ ] Deny microphone permission when prompted
- [ ] App should show error
- [ ] Offer to grant permission

### Test 5: Call Interruption
1. Start call
2. Close browser tab mid-conversation
3. Expected: Graceful cleanup on backend
4. Session can be resumed if needed

---

## Performance Testing

### Response Times

**Measure with DevTools Network tab:**

1. **Call Start** (including greeting TTS)
   - Expected: 2-3 seconds
   - [ ] Acceptable: < 5 seconds

2. **Agent Response** (including LLM + TTS)
   - Expected: 1-2 seconds
   - [ ] Acceptable: < 5 seconds

3. **Speech Recognition**
   - Expected: 2-5 seconds
   - [ ] Acceptable: < 10 seconds

**Total per turn:** 5-10 seconds typical

### Bandwidth Usage

1. Monitor DevTools → Network
2. Check payload sizes:
   - [ ] Request: < 1 KB
   - [ ] Response: < 50 KB (due to base64 audio)
   - [ ] Audio file: ~45 KB per 30 seconds of speech

---

## Stress Testing

### Test: Multiple Concurrent Calls

```python
import requests
import threading

def make_call(call_num):
    response = requests.post('http://localhost:8111/api/call/start')
    print(f"Call {call_num}: {response.status_code}")

threads = []
for i in range(5):
    t = threading.Thread(target=make_call, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

Expected: All calls succeed independently

### Test: Long Conversation
- [ ] Run 20+ turns without error
- [ ] Memory stable (check Task Manager)
- [ ] No performance degradation

---

## Regression Testing

### Ensure Backward Compatibility

Test that existing endpoints still work:

```bash
# Test existing /api/ask endpoint
curl -X POST http://localhost:8111/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about industrial parks in Madhya Pradesh"}'
```

- [ ] Returns normal response
- [ ] No impact from voice call changes

---

## UAT (User Acceptance Testing)

### Scenario 1: First-Time Investor
**User Profile:** New to industrial investment, looking for information

**Test Flow:**
1. Investor opens call interface
2. Specifies interest: "Electronics manufacturing"
3. Agent explains available options
4. Investor asks clarifying questions
5. Agent provides specific recommendations
6. Call ends with actionable next steps

**Success Criteria:**
- [ ] Felt like talking to human advisor
- [ ] Got useful information
- [ ] No technical issues
- [ ] Would use again

### Scenario 2: Experienced Investor
**User Profile:** Knows what they want, wants specific details

**Test Flow:**
1. Investor specifies: "Pharma, Indore, ₹100 crore"
2. Agent quickly provides matching options
3. Investor asks about compliance, certifications
4. Agent provides detailed answers
5. Investor schedules follow-up

**Success Criteria:**
- [ ] Fast, efficient conversation
- [ ] Technical questions answered
- [ ] Professional interaction
- [ ] Feels like executive support

---

## Post-Launch Monitoring

### Metrics to Track

1. **Call Duration**
   - Average: ~5-10 minutes
   - Target: > 5 minutes (engagement)

2. **Turn Count**
   - Average: 8-12 turns per call
   - Target: > 8 (depth of conversation)

3. **Error Rate**
   - Target: < 1%
   - Monitor: Server logs, user reports

4. **Audio Quality**
   - Successful playback: > 95%
   - Monitor: User feedback

5. **Conversion Rate**
   - Calls → Inquiries: Target > 30%
   - Inquiries → Site Visits: Target > 50%

---

## Sign-Off Checklist

### Development Team
- [ ] All code reviewed
- [ ] No syntax errors
- [ ] Tests passing
- [ ] Logging working
- [ ] Documentation complete

### QA Team
- [ ] All test cases passed
- [ ] Browser compatibility verified
- [ ] Error handling tested
- [ ] Performance acceptable
- [ ] User feedback positive

### Product Team
- [ ] Feature requirements met
- [ ] UX flow validated
- [ ] Acceptance criteria satisfied
- [ ] Stakeholder approval

### Operations Team
- [ ] Environment ready
- [ ] Monitoring configured
- [ ] Backup procedures documented
- [ ] Rollback plan ready

---

## Deployment Checklist

Before deploying to production:

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Documentation updated
- [ ] API keys configured
- [ ] Monitoring setup
- [ ] Backup created
- [ ] Rollback procedure ready
- [ ] Stakeholder notification sent
- [ ] Support team trained
- [ ] Demo prepared

---

## Support Troubleshooting Guide

For support team to use during initial rollout:

| Issue | Solution |
|-------|----------|
| No audio | Check speaker volume, reload page |
| Mic not working | Allow microphone permission, restart browser |
| Agent doesn't respond | Check GROQ_API_KEY, verify LLM connection |
| Robotic sounding | Normal behavior - optimize prompts |
| Call drops | Check internet connection, try again |
| Wrong information | Known limitation - verify with dataset |

---

**Testing Date**: January 22, 2026  
**Status**: ✅ Ready for UAT  
**Next**: Stakeholder sign-off
