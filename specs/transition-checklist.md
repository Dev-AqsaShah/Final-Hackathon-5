# Transition Checklist: General Agent → Custom Agent

## 1. From Incubation (Must Have Before Proceeding)
- [x] Working prototype that handles basic queries
- [x] Documented edge cases (13+ documented)
- [x] Working system prompt (in prompts.py)
- [x] MCP tools defined and tested (7 tools in mcp_server.py)
- [x] Channel-specific response patterns identified
- [x] Escalation rules finalized (in escalation-rules.md)
- [x] Performance baseline measured (~2s, 85% accuracy)

## 2. Transition Steps
- [x] Created production folder structure
- [x] Extracted prompts to prompts.py
- [x] Converted MCP tools to @function_tool
- [x] Added Pydantic input validation to all tools
- [x] Added error handling to all tools
- [x] Created transition test suite

## 3. Ready for Production Build
- [x] Database schema designed (PostgreSQL + pgvector)
- [x] Kafka topics defined (9 topics)
- [x] Channel handlers outlined (Gmail, WhatsApp, Web Form)
- [x] Kubernetes resource requirements set
- [x] API endpoints listed

## Working System Prompt
See: production/agent/prompts.py → CUSTOMER_SUCCESS_SYSTEM_PROMPT

## Channel Response Patterns
- Email: Formal, Dear/Best regards, <500 words, ticket ID in footer
- WhatsApp: ≤300 chars, no greeting, emoji ok, 'human' trigger word
- Web Form: Semi-formal, ≤300 words, ticket ID, link to support portal

## Escalation Rules (Finalized)
- legal/lawyer/sue → legal team (CRITICAL)
- refund/chargeback → billing team
- pricing/enterprise → sales team
- human/agent → senior_support
- sentiment < 0.3 → senior_support
- 2 failed searches → senior_support
- security breach → engineering (CRITICAL)
