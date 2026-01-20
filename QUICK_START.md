# Quick Start Guide - Enhanced Backend Features

## Installation & Setup

### 1. Install Required Packages
```bash
pip install pydantic sentence-transformers faiss-cpu
```

### 2. Start the Server
```bash
uvicorn app.main:app --reload
```

---

## Using the Enhanced API

### Basic Query

**Request:**
```bash
curl -X POST "http://localhost:8000/api/madhya_pradesh/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What industrial parks are available in Madhya Pradesh?"
  }'
```

**Response:**
```json
{
  "answer": "Madhya Pradesh has several industrial parks...\n\n**Sources:**\n1. Industrial Policy PDF (page 5) - Section: Parks",
  "state": "madhya_pradesh",
  "confidence_score": 0.87,
  "hallucination_risk": 0.12,
  "tools_used": ["search_policy", "get_parks"],
  "citations": [
    {
      "source_id": "chunk_123",
      "source_name": "MP_Policy.pdf",
      "page": 5,
      "section": "Industrial Parks",
      "relevance_score": 0.8
    }
  ],
  "validation": {
    "is_valid": true,
    "issues": [],
    "warnings": []
  },
  "metadata": {
    "request_id": "a1b2c3d4",
    "execution_time_ms": 2341,
    "data_sources_count": 3
  }
}
```

---

## Key Response Fields Explained

### `confidence_score` (0-1)
- **0.9-1.0**: Very confident, well-supported by data
- **0.7-0.9**: Good confidence, mostly supported
- **0.5-0.7**: Moderate confidence, some gaps
- **<0.5**: Low confidence, use with caution

### `hallucination_risk` (0-1)
- **0.0-0.2**: Safe, low hallucination risk
- **0.2-0.5**: Moderate risk, review response
- **>0.5**: High risk, response may contain invented data

### `citations`
Each citation includes:
- `source_name`: PDF/document name
- `page`: Page number in document
- `section`: Document section if available
- `relevance_score`: How relevant to the question (0-1)

### `validation`
- `is_valid`: Whether response passed all checks
- `issues`: Critical problems found
- `warnings`: Non-critical warnings

---

## Example Queries & Expected Results

### Query 1: Industrial Policy Question
```json
{
  "question": "What incentives are available for automotive manufacturing?"
}
```
**Expected:**
- ✅ High confidence (should reference specific policy sections)
- ✅ Multiple citations from policy documents
- ✅ Specific incentive amounts/percentages
- ❌ No speculation about future benefits

### Query 2: Location-Based Question
```json
{
  "question": "Where can I find industrial plots in Indore?"
}
```
**Expected:**
- ✅ References to specific parks in Indore
- ✅ Number of available plots
- ✅ Size and rate information
- ✅ Infrastructure details

### Query 3: Complex Analysis
```json
{
  "question": "Compare incentives for textile and pharmaceutical industries"
}
```
**Expected:**
- ✅ Multiple policy citations
- ✅ Clear comparison structure
- ✅ Specific tax breaks/subsidies mentioned
- ✅ Confidence score accounts for comparison complexity

---

## Interpreting Validation Results

### Valid Response (✅)
```json
"validation": {
  "is_valid": true,
  "issues": [],
  "warnings": []
}
```
→ Safe to use directly

### Response with Warnings (⚠️)
```json
"validation": {
  "is_valid": true,
  "issues": [],
  "warnings": [
    "Low citation coverage for response length"
  ]
}
```
→ Use but verify important claims

### Invalid Response (❌)
```json
"validation": {
  "is_valid": false,
  "issues": [
    "Response mentions parks without specific names",
    "Numerical claims without policy backing"
  ],
  "warnings": []
}
```
→ Do not use without reviewing

---

## Understanding Confidence Scores

### High Confidence (0.8+)
```
Question: "What is the maximum subsidy for power generation?"
Response includes: Specific policy references, percentage, conditions
Confidence: 0.92 ✅
```

### Moderate Confidence (0.6-0.8)
```
Question: "Best locations for electronics manufacturing?"
Response includes: Park names, advantages, some general statements
Confidence: 0.71 ⚠️
Reason: Some subjective assessment mixed with facts
```

### Low Confidence (<0.6)
```
Question: "Future investment trends in the state?"
Response includes: Speculation, future projections
Confidence: 0.38 ❌
Reason: Too speculative, insufficient data backing
```

---

## Monitoring & Debugging

### Check Performance Metrics
```bash
curl http://localhost:8000/api/health
```

### Enable Debug Logging
The system automatically logs all requests. Check logs for:
- Tool execution times
- Validation results
- Hallucination scores
- Citation coverage

### View Audit Trail
```python
from app.core.observability import get_audit_logger
logger = get_audit_logger()
recent = logger.get_audit_summary(limit=50)
```

---

## Best Practices

### ✅ DO:
- Ask specific, concrete questions
- Request citation of policies
- Compare different options systematically
- Verify large numbers against sources
- Use responses as research starting points

### ❌ DON'T:
- Assume low-confidence responses are accurate
- Use responses for regulatory compliance without verification
- Ask speculative "future" questions
- Ignore hallucination risk warnings
- Skip checking the citations

---

## Error Handling

### Invalid State
```json
{
  "answer": "Invalid state. Available states: madhya_pradesh, maharashtra",
  "error": "Invalid state. Available states: madhya_pradesh, maharashtra",
  "confidence_score": 0.0,
  "metadata": {"success": false}
}
```

### Server Error
```json
{
  "answer": "Error processing request: [error details]",
  "error": "[detailed error message]",
  "confidence_score": 0.0,
  "metadata": {"success": false, "request_id": "abc123"}
}
```

---

## Advanced Usage

### Access Request Metadata
```python
response = {
    # ... other fields ...
    "metadata": {
        "request_id": "a1b2c3d4",        # Unique request ID
        "execution_time_ms": 2341,        # Total time taken
        "data_sources_count": 3           # Number of sources used
    }
}
# Use request_id to trace through logs
```

### Check Data Source Coverage
```python
response = {
    # ...
    "metadata": {
        "data_sources_count": 3
    }
}
# Higher count generally means more thorough answer
```

### Track Tool Usage
```python
response = {
    # ...
    "tools_used": ["search_policy", "get_parks"]
}
# Tells you which data sources were consulted
```

---

## Troubleshooting

### Low Confidence Score?
- Check if question is too vague
- Ensure data exists for the query
- Check `hallucination_risk` - if high, response may have invented details
- Look at `validation.warnings` for hints

### Missing Citations?
- Response may not reference specific policies
- Check if policy data is loaded
- Try rephrasing with policy-specific terms

### "No results found"?
- Question may not match available policies
- Try broader search terms
- Check state name spelling
- Verify data files are present

---

## Example: Building Better Questions

### ❌ Poor Question
```
"Tell me about industrial parks"
```
→ Too vague, many interpretations

### ✅ Better Question
```
"List all operational industrial parks in Madhya Pradesh"
```
→ Specific, actionable, verifiable

### ✅ Even Better
```
"What are the incentives for automotive manufacturing in Madhya Pradesh industrial parks?"
```
→ Specific topic, location, industry - will get high-quality answer

---

## API Response Timeline

Understanding what happens during processing:

1. **Input Validation** (10-50ms)
   - Validates state and question format
   
2. **Tool Execution** (500-2000ms)
   - Searches policies
   - Fetches parks and plots
   - Finds infrastructure
   
3. **Response Generation** (300-1000ms)
   - LLM generates response with context
   
4. **Validation Pipeline** (100-500ms)
   - Checks for hallucinations
   - Verifies citations
   - Calculates confidence
   
5. **Response Formatting** (50-100ms)
   - Adds metadata and citations

**Total: 1-4 seconds typically**

---

## Next Steps

1. **Start Testing**: Try different types of questions
2. **Monitor Confidence Scores**: Understand patterns
3. **Check Citations**: Verify against source documents
4. **Review Logs**: Understand system behavior
5. **Iterate**: Refine questions for better results

**Your backend is now ready for production use!** 🚀
