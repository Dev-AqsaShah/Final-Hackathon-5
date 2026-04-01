# Runbook — TechNova Customer Success FTE

> Incident response and operational guide for on-call engineers.

---

## Service Overview

| Component | Port | Health Check |
|-----------|------|--------------|
| FastAPI API | 8002 | `GET /health` |
| PostgreSQL | 5432 | `docker ps` |
| Web Form (Next.js) | 3000 | Browser |
| Kafka (optional) | 9092 | `docker ps` |

---

## Common Incidents

### 1. API Not Responding

**Symptoms:** `curl http://localhost:8002/health` returns connection refused

**Steps:**
```bash
# Check if process is running
netstat -ano | findstr :8002

# Restart API
cd D:/Final-Hackathon-5
python -m uvicorn production.api.main:app --port 8002 --reload

# Verify
curl http://localhost:8002/health
```

**Note:** Port 8000 is occupied by Docker Desktop. Always use port 8002.

---

### 2. Database Connection Failed

**Symptoms:** API starts with warning `Database not available`

**Steps:**
```bash
# Check postgres container
docker ps | grep postgres

# Start if stopped
cd production
docker-compose up postgres -d

# Verify tables exist
docker exec -it production-postgres-1 psql -U postgres -d fte_db -c "\dt"
# Should show 9 tables
```

---

### 3. Agent Not Responding (AI calls failing)

**Symptoms:** Tickets created but no AI responses

**Diagnosis:**
```bash
# Test API key
cd D:/Final-Hackathon-5
python -c "
import anthropic, os
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
msg = client.messages.create(model='claude-haiku-4-5-20251001', max_tokens=10, messages=[{'role':'user','content':'hi'}])
print('OK:', msg.content[0].text)
"
```

**Fix:** If key is invalid, update `production/.env`:
```
ANTHROPIC_API_KEY=your-new-key-here
```
Get new key: https://console.anthropic.com → API Keys

---

### 4. Web Form Submits but Gets Error

**Symptoms:** Form returns error on submit

**Diagnosis:**
```bash
# Test endpoint directly
curl -X POST http://localhost:8002/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"t@t.com","subject":"Test sub","category":"general","message":"Test message here ok"}'
```

**Common causes:**
- API not running → restart uvicorn
- CORS issue → check browser console for CORS errors
- Validation error → check field lengths (name≥2, subject≥5, message≥10)

---

### 5. Kafka Not Available (Expected)

**Symptoms:** Warning `aiokafka not installed - Kafka disabled`

This is **normal** in development. The system runs in direct mode.

To enable Kafka:
```bash
cd production
docker-compose up kafka -d
pip install aiokafka
# Restart API
```

---

### 6. Port 8000 Already Taken

**Symptoms:** `uvicorn` on port 8000 fails

**Root cause:** Docker Desktop uses port 8000 internally.

**Fix:** Always use port 8002:
```bash
python -m uvicorn production.api.main:app --port 8002
```

---

## Health Check Procedure

Run this before any demo or submission:

```bash
# 1. API health
curl -s http://localhost:8002/health | python -m json.tool

# 2. Submit test ticket
curl -s -X POST http://localhost:8002/support/submit \
  -H "Content-Type: application/json" \
  -d '{"name":"Health Check","email":"hc@test.com","subject":"Health check ticket","category":"general","message":"This is a health check submission test."}' \
  | python -m json.tool

# 3. Run all tests
cd D:/Final-Hackathon-5
python -m pytest production/tests/ -v --tb=short -q

# 4. Check frontend builds
cd src/web-form && npm run build
```

All 4 steps should succeed.

---

## Run All Tests

```bash
cd D:/Final-Hackathon-5
python -m pytest production/tests/test_agent.py production/tests/test_channels.py production/tests/test_e2e.py -v
```

Expected: **46 passed**

---

## Load Test Procedure

```bash
pip install locust
locust -f tests/load_test.py --host http://localhost:8002 --headless \
  --users 20 --spawn-rate 2 --run-time 60s
```

**Pass criteria:**
- 0% failure rate on `/support/submit`
- Median response time < 500ms
- `/health` always 200

---

## Escalation Contacts (Fictional)

| Issue | Team | Priority |
|-------|------|----------|
| Legal threats | legal@technova.io | CRITICAL |
| Security breach | security@technova.io | CRITICAL |
| Refund disputes | billing@technova.io | HIGH |
| Pricing queries | sales@technova.io | NORMAL |
| Technical issues | support@technova.io | NORMAL |

---

## Environment Variables Reference

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...     # Claude API key

# Database (Docker)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_DB=fte_db

# Optional — Gmail
GMAIL_CREDENTIALS={"type":"service_account",...}

# Optional — WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```
