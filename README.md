# CRM Digital FTE Factory — Hackathon 5

> **24/7 AI Customer Success Agent** for TechNova SaaS  
> Handles customer queries from **3 channels**: Gmail · WhatsApp · Web Form  
> Powered by **Anthropic Claude** via LiteLLM + OpenAI Agents SDK

---

## Project Overview

This project implements the complete **Agent Maturity Model** — from an exploratory prototype to a production-grade Custom Agent deployed on Kubernetes.

```
Stage 1 (Incubation)   →  Stage 2 (Specialization)  →  Stage 3 (Testing)
Prototype + MCP           FastAPI + PostgreSQL           E2E + Load Tests
Claude explores           Claude executes                Claude verified
```

---

## Architecture

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    Gmail    │  │  WhatsApp   │  │  Web Form   │
│  (Webhook)  │  │  (Twilio)   │  │  (Next.js)  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       └────────────────┼─────────────────┘
                        ▼
              ┌─────────────────┐
              │   FastAPI API   │  ← port 8002
              │  (main.py)      │
              └────────┬────────┘
                       ▼
              ┌─────────────────┐     ┌──────────────┐
              │  Claude Agent   │────▶│  PostgreSQL  │
              │  (LiteLLM)      │     │  (9 tables)  │
              └─────────────────┘     └──────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.12+
- Docker Desktop (for PostgreSQL)
- Node.js 18+ (for web form)

### 1. Clone & Setup

```bash
git clone https://github.com/Dev-AqsaShah/Final-Hackathon-5.git
cd Final-Hackathon-5
```

### 2. Environment Variables

```bash
cp production/.env.example production/.env
# Edit production/.env and set:
# ANTHROPIC_API_KEY=your-key-here
```

### 3. Start Database

```bash
cd production
docker-compose up postgres -d
```

### 4. Install Python Dependencies

```bash
pip install -r production/requirements.txt
```

### 5. Start API Server

```bash
# From project root
python -m uvicorn production.api.main:app --port 8002 --reload
```

API is now at: `http://localhost:8002`

### 6. Start Web Form (Frontend)

```bash
cd src/web-form
npm install
npm run dev
```

Web form is now at: `http://localhost:3000`

---

## Testing

### Run All Tests

```bash
# From project root
python -m pytest production/tests/ -v
```

### Expected Output

```
production/tests/test_agent.py      — 15 tests PASSED
production/tests/test_channels.py   — 10 tests PASSED
production/tests/test_e2e.py        — 21 tests PASSED
```

### Load Testing (Locust)

```bash
pip install locust
locust -f tests/load_test.py --host http://localhost:8002
# Open http://localhost:8089
# Set: Users=50, Spawn rate=5, then Start
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/health` | Health check — all channels status |
| `POST` | `/support/submit` | Submit web form ticket |
| `GET`  | `/support/ticket/{id}` | Get ticket status |
| `GET`  | `/customers/lookup?email=` | Look up customer across channels |
| `GET`  | `/metrics/channels` | Channel performance metrics |
| `POST` | `/webhooks/gmail` | Gmail Pub/Sub webhook |
| `POST` | `/webhooks/whatsapp` | Twilio WhatsApp webhook |
| `GET`  | `/conversations/{id}` | Full conversation history |

### Example: Submit Support Ticket

```bash
curl -X POST http://localhost:8002/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "jane@company.com",
    "subject": "Cannot reset my password",
    "category": "technical",
    "priority": "medium",
    "message": "I have been trying to reset my password but no email arrives."
  }'
```

Response:
```json
{
  "ticket_id": "a3f7c2d1-...",
  "message": "Thank you! Our AI assistant will respond shortly.",
  "estimated_response_time": "Usually within 5 minutes"
}
```

---

## Project Structure

```
Final-Hackathon-5/
├── context/                    # TechNova company context for AI
│   ├── company-profile.md
│   ├── product-docs.md
│   ├── escalation-rules.md
│   └── brand-voice.md
├── src/
│   ├── agent/                  # Stage 1: Prototype
│   │   ├── prototype.py        # Working Claude prototype
│   │   ├── mcp_server.py       # MCP Server (7 tools)
│   │   └── skills.py           # 5 agent skills
│   └── web-form/               # Next.js support form UI
│       └── src/components/SupportForm.jsx
├── production/
│   ├── agent/
│   │   ├── customer_success_agent.py   # Production agent (LiteLLM + Claude)
│   │   ├── tools.py                    # @function_tool definitions
│   │   ├── prompts.py                  # System prompts
│   │   └── embeddings.py               # pgvector embeddings
│   ├── channels/
│   │   ├── gmail_handler.py            # Gmail API integration
│   │   ├── whatsapp_handler.py         # Twilio WhatsApp
│   │   └── web_form_handler.py         # Web form handler
│   ├── workers/
│   │   ├── kafka_client.py             # Kafka producer/consumer
│   │   └── message_processor.py        # Unified message processor
│   ├── api/main.py                     # FastAPI application
│   ├── database/
│   │   ├── schema.sql                  # PostgreSQL schema (9 tables)
│   │   └── queries.py                  # Database access functions
│   ├── tests/
│   │   ├── test_agent.py               # Agent + skill tests (15 tests)
│   │   ├── test_channels.py            # Channel handler tests (10 tests)
│   │   └── test_e2e.py                 # End-to-end tests (21 tests)
│   ├── k8s/deployment.yaml             # Kubernetes manifests
│   ├── docker-compose.yml
│   └── Dockerfile
├── specs/
│   ├── discovery-log.md
│   ├── customer-success-fte-spec.md
│   └── transition-checklist.md
└── tests/
    └── load_test.py                    # Locust load tests
```

---

## Channel Configuration

### Web Form (Active — No credentials needed)
Works out of the box. Frontend at `localhost:3000` → API at `localhost:8002`.

### Gmail (Mock mode by default)
To enable real Gmail:
1. Create Google Cloud project
2. Enable Gmail API + Pub/Sub
3. Download credentials JSON
4. Set `GMAIL_CREDENTIALS` in `.env` (JSON string)

### WhatsApp via Twilio (Mock mode by default)
To enable real WhatsApp:
1. Create Twilio account
2. Join WhatsApp Sandbox
3. Set in `.env`:
   ```
   TWILIO_ACCOUNT_SID=ACxxxxxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ```

---

## Escalation Rules

| Trigger | Action | Team |
|---------|--------|------|
| "lawyer", "legal", "sue" | Immediate escalation | Legal (CRITICAL) |
| "refund", "chargeback" | Escalate | Billing |
| "price", "how much", "enterprise plan" | Escalate | Sales |
| "human", "agent", "real person" | Escalate | Senior Support |
| Sentiment score < 0.3 | Escalate | Senior Support |
| 2 failed knowledge searches | Escalate | Senior Support |
| "hacked", "breach", "unauthorized" | Escalate | Engineering (CRITICAL) |

---

## Kubernetes Deployment

```bash
kubectl apply -f production/k8s/deployment.yaml

# Verify pods are running
kubectl get pods -n customer-success-fte

# Check logs
kubectl logs -n customer-success-fte deployment/fte-api
```

---

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Response time (AI) | < 3 seconds | ✅ |
| Accuracy on test set | > 85% | ✅ |
| Escalation rate | < 25% | ✅ |
| Cross-channel ID accuracy | > 95% | ✅ |
| API uptime | 99.9% | ✅ |
| Test coverage | 46 tests | ✅ |

---

## Built With

- **AI**: Anthropic Claude (claude-sonnet-4-6) via LiteLLM
- **Agent Framework**: OpenAI Agents SDK
- **Backend**: FastAPI + Python 3.12
- **Database**: PostgreSQL 16 + pgvector
- **Event Streaming**: Apache Kafka (optional)
- **Frontend**: Next.js 14 + Tailwind CSS
- **Channels**: Gmail API + Twilio WhatsApp
- **Infrastructure**: Docker + Kubernetes
