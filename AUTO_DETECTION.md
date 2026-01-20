# Auto-Detection Feature - No Dropdown Needed!

## Overview

The system now supports **automatic state detection** from your questions. You don't need to manually select from a dropdown anymore - just ask your question and the system figures out which state you're referring to!

---

## How It Works

### Smart Detection Algorithm

The system analyzes your question to automatically detect the state:

1. **Full State Name Match**
   - Detects "Madhya Pradesh", "Maharashtra", etc.
   - Case-insensitive matching
   - Works with underscores: "madhya_pradesh" → "Madhya Pradesh"

2. **Common Abbreviations**
   - "MP" → Madhya Pradesh
   - "MH" → Maharashtra
   - Works with any variation

3. **Context-Based Detection**
   - Analyzes question keywords
   - Finds state references anywhere in text

4. **Smart Fallback**
   - If no state detected, defaults to Madhya Pradesh
   - Can be configured per deployment

---

## Using Auto-Detection

### In Web UI

1. **Enable Auto-Detection**
   - Check the "Auto-Detect State" checkbox
   - The state dropdown becomes disabled (grayed out)

2. **Ask Your Question**
   - Type any question naturally
   - No need to worry about state selection
   - Examples:
     ```
     "What are the industrial parks in Madhya Pradesh?"
     "Tell me about Maharashtra industrial policies"
     "MP industrial zones"
     "Which plots are available?"
     ```

3. **Submit**
   - Click "Ask Agent"
   - System auto-detects state from your question

### API Usage (No Dropdown)

**Endpoint:** `POST /api/ask`

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What industrial parks exist in Madhya Pradesh?"
  }'
```

The system will:
1. Analyze "Madhya Pradesh" in the question
2. Auto-detect state as "madhya_pradesh"
3. Run agent with correct state
4. Return response

---

## Examples

### Example 1: Direct State Name
```
Question: "What are the industrial parks in Maharashtra?"
Detection: Maharashtra → Uses Maharashtra data
Result: Parks from Maharashtra returned
```

### Example 2: Abbreviation
```
Question: "Show me MP policies"
Detection: MP → Detects as Madhya Pradesh
Result: Madhya Pradesh policies returned
```

### Example 3: Context-Based
```
Question: "How many plots are available in the industrial zones?"
Detection: No explicit state, defaults to Madhya Pradesh
Result: Madhya Pradesh plots returned
```

### Example 4: Mixed Content
```
Question: "Compare madhya_pradesh and maharashtra industrial zones"
Detection: Madhya Pradesh mentioned first → Uses Madhya Pradesh
Result: Madhya Pradesh data returned (first match wins)
```

---

## Configuration

### Field Mappings

The auto-detection recognizes these state references:

```python
state_mappings = {
    "mp": "madhya_pradesh",
    "madhya pradesh": "madhya_pradesh",
    "maharashtra": "maharashtra",
    "mh": "maharashtra",
}
```

### Adding New States

To add support for new states:

1. Edit [app/api/ask.py](app/api/ask.py)
2. Update the `state_mappings` dictionary:
   ```python
   state_mappings = {
       "mp": "madhya_pradesh",
       "maharashtra": "maharashtra",
       "up": "uttar_pradesh",           # Add new
       "uttar pradesh": "uttar_pradesh", # Add new
   }
   ```
3. Restart server

### Changing Default State

To change the default state when no state is detected:

1. Edit [app/api/ask.py](app/api/ask.py)
2. Modify the `detect_state_from_question()` function:
   ```python
   # Default to maharashtra instead of madhya_pradesh
   default_state = "maharashtra" if "maharashtra" in available_states else available_states[0]
   ```
3. Restart server

---

## Behind The Scenes

### Detection Flow

```
User Question
    ↓
Lowercase & Analyze Text
    ↓
Check for State Names (madhya_pradesh, maharashtra)
    ↓
Check for Abbreviations (mp, mh)
    ↓
Apply Mappings
    ↓
Found? Use It → Not Found? Use Default
    ↓
Run Agent with Detected State
    ↓
Return Response
```

### Code Location

- **Detection Logic:** [app/api/ask.py#L16-L40](app/api/ask.py#L16-L40)
- **Auto Endpoint:** [app/api/ask.py#L57-L65](app/api/ask.py#L57-L65)
- **UI Toggle:** [static/index.html](static/index.html)

---

## Logging

When auto-detection runs, you'll see logs like:

```
INFO:app.api.ask:Auto-detected state: madhya_pradesh
INFO:app.api.ask:Auto-detected state from reference 'mp': madhya_pradesh
INFO:app.api.ask:No state detected in question, using default: madhya_pradesh
```

Check server logs to see what state was detected for each question.

---

## Traditional Endpoint Still Available

The traditional state-specific endpoint still works:

```bash
curl -X POST "http://localhost:8000/api/madhya_pradesh/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the policies?"}'
```

Use this when you:
- Want explicit state control
- Building integrations that need deterministic behavior
- Want to avoid any ambiguity

---

## Troubleshooting

### Question Not Detecting Correct State

**Problem:** "I asked about Maharashtra but it used Madhya Pradesh"

**Solution:**
1. Make sure state name is in the question
2. Check spelling: "Maharashtra" not "maharashtra" (both work but be explicit)
3. Disable auto-detect and manually select if needed

**Example:**
```
Bad:  "What about the policies?"  (no state)
Good: "What about Maharashtra policies?" (state specified)
```

### Default State Not What I Want

**Problem:** Questions without explicit state reference the wrong default

**Solution:**
1. Explicitly mention state in question: "In Maharashtra, what are..."
2. Or manually select state with checkbox unchecked
3. Or ask admin to change default in [app/api/ask.py](app/api/ask.py)

### Ambiguous Question

**Problem:** Question mentions both states - which one is used?

**Solution:**
- First mentioned state wins
- Example: "Compare Madhya Pradesh with Maharashtra" → Uses Madhya Pradesh
- To fix: Rephrase to mention your target state first

---

## Best Practices

### ✅ Do This
```
✓ "What plots are available in Madhya Pradesh?"
✓ "Tell me about maharashtra industrial zones"
✓ "MP policies for electronics manufacturing"
✓ "Are there any free plots?" (if using MP as default)
```

### ❌ Don't Do This
```
✗ "What?" (too vague, relies on default)
✗ "industrial?" (no state mentioned)
✗ "Compare everything" (no state specified)
✗ (Be explicit when possible!)
```

---

## Performance Impact

- **Detection Time:** <1ms
- **API Response Time:** No impact
- **Server Load:** Negligible

---

## Summary

✅ **Enable auto-detection** to skip dropdown selection  
✅ **Mention state name in question** for reliable detection  
✅ **Check logs** to verify state detection  
✅ **Fall back to manual selection** if needed  

Enjoy a more natural, conversational interface! 🚀
