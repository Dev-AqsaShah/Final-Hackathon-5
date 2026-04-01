# Discovery Log - Customer Success FTE

## Exploration Session: Initial Analysis

### Channel Patterns Discovered

#### Email Channel
- Messages tend to be longer and more detailed
- Customers provide full context upfront
- Subject line often contains the issue summary
- Formal tone expected in response
- Thread continuity important (customers reply to same thread)
- Some customers CC their managers → indicates urgency

#### WhatsApp Channel
- Very short messages (often 1-5 words)
- Informal, conversational style
- Multiple messages in quick succession (fragmented thoughts)
- Customers expect FAST responses
- Emojis acceptable
- Max response: 1600 chars, preferred < 300 chars
- Trigger words: "human", "agent" → immediate escalation

#### Web Form Channel
- Structured input (category, priority, subject)
- More thoughtful messages since form guides them
- Semi-formal tone expected
- Customer expects email confirmation
- Async nature: customer may not be actively waiting

---

## Requirements Discovered During Incubation

### Functional Requirements
1. **Multi-channel intake**: Accept messages from Email, WhatsApp, and Web Form
2. **Unified customer identity**: Same customer across channels = same history
3. **Channel-aware responses**: Different style/length per channel
4. **Ticket creation**: Every interaction creates a trackable ticket
5. **Knowledge search**: Search product docs before responding
6. **Sentiment detection**: Detect frustration/anger before responding
7. **Escalation logic**: Clear rules for when to pass to humans
8. **Cross-channel history**: See all past interactions regardless of channel

### Non-Functional Requirements
1. Response time < 3 seconds (AI processing)
2. 99.9% uptime (24/7 operation)
3. Graceful error handling (never crash, always acknowledge)
4. Audit trail (log all interactions)

---

## Edge Cases Found

| # | Edge Case | Channel | How Handled | Test Written? |
|---|-----------|---------|-------------|---------------|
| 1 | Empty message | WhatsApp | Ask for clarification | Yes |
| 2 | Pricing question | Any | Escalate to sales | Yes |
| 3 | Refund request | Any | Escalate to billing | Yes |
| 4 | Legal threat | Any | Escalate to legal (critical) | Yes |
| 5 | Angry customer (caps, exclamations) | Any | Empathize + escalate | Yes |
| 6 | Customer switches channels | Any | Check cross-channel history | Yes |
| 7 | Unknown/unrecognized question | Any | 2 searches then escalate | Yes |
| 8 | Security incident report | Any | Escalate to engineering (critical) | Yes |
| 9 | Feature not in docs | Any | Do NOT promise, escalate to sales | Yes |
| 10 | Customer requests human explicitly | Any | Immediate escalation | Yes |
| 11 | Very long email (5000+ chars) | Email | Summarize, respond concisely | No |
| 12 | WhatsApp customer sends 3+ identical messages | WhatsApp | Detect loop, escalate | No |
| 13 | Customer contacts in non-English language | Any | Respond in same language if possible | No |

---

## Escalation Patterns (Finalized)

### Immediate (No Attempt to Resolve)
- Legal threats → legal team
- Refund requests → billing team
- Security incidents → engineering team
- Pricing/enterprise inquiries → sales team
- Human explicitly requested → senior support

### After Attempting Resolution
- Sentiment < 0.3 (very angry) → senior support
- 2 failed knowledge searches → senior support
- Issue unresolved for 48+ hours → escalate with history

---

## Response Style Templates (Discovered)

### Email Template
```
Dear [Name],
Thank you for reaching out to TechNova Support.
[Acknowledge issue]
[Steps / Solution]
[Offer further help]
Best regards,
TechNova Support Team | Ticket: [ID]
```

### WhatsApp Template
```
[Direct answer in <300 chars]
Ref: [ID] | Type 'human' for live agent 💬
```

### Web Form Template
```
[Acknowledge]
[Solution]
---
Ticket ID: [ID] | Need more help? support.technova.io
```

---

## Performance Baseline (Prototype)
- Average response time: ~2 seconds
- Accuracy on test set: ~85%
- Escalation rate: ~22%
- Knowledge base hit rate: ~75%
