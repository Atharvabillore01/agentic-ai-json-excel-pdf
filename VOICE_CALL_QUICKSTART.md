# 🚀 Quick Start - Voice Call Agent

## In 2 Minutes

### 1. Ensure Server is Running
```bash
cd d:\Atharva\agentic-ai\mp-industrial-fastapi
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8111 --reload
```

### 2. Set Environment Variables
Create or update `.env`:
```env
ELEVENLABS_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
LLM_PROVIDER=groq
GROQ_API_KEY=gsk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Open Voice Call Interface
```
http://localhost:8111/static/call.html
```

### 4. Start a Call
1. Click **▶️ Start Call**
2. Listen to agent greeting (plays automatically)
3. Speak when prompted
4. Continue conversation naturally
5. Click **⏹ End Call** when done

## What You Should Hear

**Agent (Opening):**
> "Hi there! I'm your industrial investment advisor. I specialize in opportunities across Madhya Pradesh. Is this your first time exploring industrial investments with us, or are you looking for something specific?"

**You speak:** "I'm interested in pharmaceutical manufacturing in Indore"

**Agent (Response):**
> "Great! We have some excellent pharmaceutical parks in Indore. Pipariya is particularly well-suited for manufacturing. Before I go deeper, what's your investment timeline - are you looking at something immediate or 12-18 months out?"

## Demo Conversation Flow

```
Turn 1: Agent greets you
Turn 2: You ask about pharma opportunities in Indore
Turn 3: Agent asks about timeline
Turn 4: You mention 12-month timeline
Turn 5: Agent shares specific park recommendations
Turn 6: You ask about infrastructure
Turn 7: Agent provides details on connectivity
Turn 8: You say "Ready to move forward"
Turn 9: Agent summarizes and suggests next steps
Turn 10: Call ends with summary
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No audio | Check speaker volume, verify ELEVENLABS_API_KEY in .env |
| Mic not working | Grant microphone permission, use Chrome/Edge |
| Agent doesn't respond | Check server logs, verify GROQ_API_KEY |
| Robotic responses | Give agent a moment - it's generating natural speech |

## Key Files

- **Frontend**: `static/call.html` - Call interface
- **Backend**: `app/api/call.py` - Call management API
- **Agent**: `app/agents/agent.py` - Response generation
- **Guide**: `VOICE_CALL_GUIDE.md` - Detailed documentation

## Next Steps

✅ Test with voice  
✅ Adjust prompts if needed (in `app/agents/agent.py`)  
✅ Add more greeting templates  
✅ Customize for your brand  

---

**Status**: Ready to test!  
**Need help?** Check VOICE_CALL_GUIDE.md for detailed docs.
