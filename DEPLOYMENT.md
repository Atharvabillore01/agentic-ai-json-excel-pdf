# Configuration & Deployment Guide

## Environment Setup

### 1. Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate
# On Windows:
.\venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt

# Additional packages (if not in requirements.txt)
pip install pydantic sentence-transformers faiss-cpu
```

### 3. Required Environment Variables
```bash
# Create .env file
GROQ_API_KEY=your_groq_api_key_here

# Optional configuration
LOG_LEVEL=INFO
DEBUG=False
```

---

## Tuning Parameters

### Semantic Chunking (`app/services/semantic_chunking.py`)

```python
# Adjust for your data size
CHUNK_SIZE = 800          # Characters per chunk
OVERLAP = 200             # Overlap between chunks
MIN_CHUNK_SIZE = 100      # Minimum viable chunk

# Larger chunks = more context but may lose specificity
# Smaller chunks = more precise but may lose context
# Recommended: 600-1000 for policies
```

**Guidance:**
- **Small documents** (< 5MB): Use larger chunks (1000+)
- **Medium documents** (5-50MB): Use default (800)
- **Large documents** (50MB+): Use smaller chunks (500)

---

### Tool Result Compression (`app/agents/tool_compressor.py`)

```python
MAX_ITEMS = 5             # Sample items to show
MAX_CHARS = 1500          # Maximum output length

# Lower values = faster processing, less context
# Higher values = more complete but uses more tokens
```

---

### Validation Thresholds (`app/agents/response_validation.py`)

```python
VALID_IF = {
    "hallucination_risk": "< 0.6",
    "data_alignment": "> 0.5", 
    "issues_count": "== 0"
}

# Adjust based on your tolerance
# Stricter (lower hallucination threshold) = safer but fewer answers
# Looser (higher threshold) = more answers but some may be risky
```

---

### Confidence Score Calculation

```python
# Default weights in response_validation.py
BASE = 0.7
- hallucination_risk * 0.3
+ data_alignment * 0.15
+ citation_coverage * 0.1
+ completeness * 0.1
- (issues_count * 0.05)

# Adjust weights based on what matters most
# Increase hallucination_risk weight for stricter standards
# Increase citation_coverage for more cited responses
```

---

### Vector Search Parameters (`app/vectorstore/policy_index.py`)

```python
K = 5                     # Number of results to return
MODEL = "all-MiniLM-L6-v2"  # Embedding model

# Return top K most similar chunks
# Larger K = more results but may include less relevant
# Recommended: 3-10 depending on response length
```

---

## Logging Configuration

### Log Levels
```python
logging.basicConfig(level=logging.INFO)

# Options:
# DEBUG   - Very verbose, all details
# INFO    - Standard logging (recommended)
# WARNING - Only warnings and errors
# ERROR   - Only errors
```

### Log Locations
```
# Default: Console output
# To file: Configure in observability.py

# Suggested log file structure:
logs/
├── requests/     # Individual request logs
├── tools/        # Tool execution logs
├── validation/   # Validation results
└── audit/        # Audit trail
```

---

## Performance Tuning

### For Speed (< 1 second response target):
```python
# 1. Reduce chunk size for faster search
CHUNK_SIZE = 400
OVERLAP = 100

# 2. Reduce tool result compression
MAX_ITEMS = 3
MAX_CHARS = 800

# 3. Cache embeddings
# Already optimized - FAISS handles this

# 4. Reduce validation checks (NOT RECOMMENDED)
# All checks are important for accuracy
```

### For Accuracy (highest confidence):
```python
# 1. Increase chunk size for context
CHUNK_SIZE = 1200
OVERLAP = 300

# 2. Return more results
K = 10
MAX_ITEMS = 10

# 3. Stricter validation
HALLUCINATION_THRESHOLD = 0.3

# 4. Enable all validation checks
# Already enabled by default
```

### For Balance:
```python
# Default settings provide good balance
# Only modify if specific performance issues occur
```

---

## Scaling Considerations

### Single Server (Current Setup)
```
Max concurrent requests: 10-20 (limited by model)
Recommended QPS: 2-5
Memory needed: 4-8 GB
Storage needed: 2-5 GB (for data + embeddings)
```

### To Scale Horizontally:
```
1. Move cache to Redis
2. Move embeddings to Weaviate/Pinecone
3. Use FastAPI with Gunicorn
4. Deploy with load balancer
5. Use separate validation worker pool
```

---

## Deployment Checklist

- [ ] Python 3.8+
- [ ] All dependencies installed
- [ ] GROQ_API_KEY configured
- [ ] Data files in `app/data/states/`
- [ ] Initial data load successful (`python -c "from app.services.loader import load_all; load_all()"`)
- [ ] Vector indexes built
- [ ] Log directories created
- [ ] SSL/TLS certificates (if production)
- [ ] CORS configured if needed
- [ ] Rate limiting configured
- [ ] Monitoring setup

---

## Production Recommendations

### 1. Use Gunicorn + Uvicorn
```bash
pip install gunicorn

# Start with 4 workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 2. Enable HTTPS
```bash
# Generate certificates or use Let's Encrypt
# Configure in FastAPI or reverse proxy

# Recommended: Use nginx as reverse proxy
```

### 3. Setup Monitoring
```python
# Use Prometheus + Grafana for metrics
# Monitor:
# - Request latency
# - Confidence scores
# - Hallucination rates
# - Tool execution times
```

### 4. Enable Caching
```python
# Redis for cache
# Weaviate for vector embeddings
# PostgreSQL for audit logs
```

### 5. Rate Limiting
```python
# Limit requests per IP
# Implement token bucket algorithm
# Or use third-party service (Auth0, etc)
```

### 6. Error Monitoring
```bash
pip install sentry-sdk

# Setup Sentry for error tracking
# Automatically logs all exceptions
```

---

## Database Migration (Optional)

If moving from in-memory cache to database:

```python
# From: In-memory cache in core/cache.py
cache = {"states": {}, "last_updated": None}

# To: PostgreSQL database
class State(Base):
    id: int
    name: str
    parks: List[Park]
    plots: List[Plot]
    policies: List[Policy]
```

---

## Backup & Recovery

### Daily Backup
```bash
#!/bin/bash
# Backup all data
cp -r app/data/states backup/$(date +%Y-%m-%d)
```

### Recovery
```bash
# Restore from backup
cp -r backup/YYYY-MM-DD app/data/states
# Restart server and rebuild indexes
```

---

## Troubleshooting Configuration

### Issue: Slow Response Times
**Solution:**
1. Check if data is fully loaded: `cache["states"]`
2. Verify vector indexes are built
3. Reduce MAX_ITEMS in compressor
4. Check server resources (CPU, RAM)

### Issue: Low Confidence Scores
**Solution:**
1. Check if data is comprehensive
2. Verify policies are loaded
3. Reduce hallucination threshold
4. Check validation thresholds

### Issue: High Hallucination Risk
**Solution:**
1. Stricter guardrails in prompt
2. More validation checks
3. Reduce model temperature (if configurable)
4. Better question analysis

### Issue: Memory Usage Too High
**Solution:**
1. Reduce chunk size
2. Use lazy loading for embeddings
3. Clear old audit logs
4. Move to streaming responses

---

## Testing Configuration

### Local Development
```python
DEBUG = True
LOG_LEVEL = "DEBUG"
MAX_ITEMS = 10  # Show more results
```

### Staging
```python
DEBUG = False
LOG_LEVEL = "INFO"
MAX_ITEMS = 5
# Enable monitoring but less strict
```

### Production
```python
DEBUG = False
LOG_LEVEL = "WARNING"
MAX_ITEMS = 5
# Strict validation, comprehensive logging
```

---

## API Configuration

### CORS (if needed)
```python
# In app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
```

### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/{state}/ask")
@limiter.limit("10/minute")
async def ask_question(state: str, payload: AskRequest):
    # Limit to 10 requests per minute per IP
```

---

## Monitoring Setup

### Key Metrics to Track
1. **Request Latency** - Should be 1-4 seconds
2. **Confidence Scores** - Target > 0.7 average
3. **Hallucination Rate** - Target < 20% of requests
4. **Tool Success Rate** - Target > 95%
5. **Validation Pass Rate** - Target > 80%

### Dashboard Queries
```sql
-- Average confidence by day
SELECT DATE(timestamp), AVG(confidence_score)
FROM requests
GROUP BY DATE(timestamp)

-- Hallucination risk distribution
SELECT 
  CASE WHEN hallucination_risk < 0.3 THEN 'Low'
       WHEN hallucination_risk < 0.6 THEN 'Medium'
       ELSE 'High' END as risk_level,
  COUNT(*) as count
FROM requests
GROUP BY risk_level

-- Tool execution times
SELECT tool, AVG(execution_time_ms), MAX(execution_time_ms)
FROM tool_calls
GROUP BY tool
```

---

## Maintenance Tasks

### Weekly
- [ ] Check error logs for patterns
- [ ] Review confidence score trends
- [ ] Verify all states are indexed
- [ ] Check disk usage

### Monthly
- [ ] Update data files if changed
- [ ] Rebuild vector indexes
- [ ] Archive old logs
- [ ] Review monitoring dashboards

### Quarterly
- [ ] Update dependencies
- [ ] Performance optimization review
- [ ] Security audit
- [ ] Scaling assessment

---

## Security Best Practices

1. **API Keys**: Never commit GROQ_API_KEY to repo
2. **Input Validation**: Already implemented (don't remove)
3. **Output Sanitization**: Already implemented
4. **Rate Limiting**: Configure for production
5. **HTTPS**: Required for production
6. **Authentication**: Add if needed (OAuth2, etc)
7. **Audit Logging**: Already comprehensive
8. **Data Privacy**: Ensure compliance (GDPR, etc)

---

## Emergency Procedures

### If Hallucination Rate Spikes
```
1. Reduce HALLUCINATION_RISK_THRESHOLD
2. Increase validation checks
3. Review recent data changes
4. Check model behavior (may need restart)
```

### If Service is Down
```
1. Check logs for errors
2. Verify data files exist
3. Rebuild vector indexes
4. Restart service
5. Monitor confidence scores
```

### If Memory Leaks
```
1. Reduce chunk cache
2. Clear old audit logs
3. Reduce embedding cache
4. Use memory profiler
5. Consider database migration
```

---

**Your system is ready for production deployment!** 🎉
