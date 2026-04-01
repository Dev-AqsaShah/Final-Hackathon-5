# Escalation Rules - When to Involve Humans

## Immediate Escalation (Priority: CRITICAL)

These situations must be escalated immediately without attempting to resolve:

1. **Legal Threats**
   - Keywords: "lawyer", "legal", "sue", "lawsuit", "attorney", "court"
   - Action: Escalate to Legal + Senior Support
   - Response: "I understand your concern. I'm connecting you with our senior support team immediately."

2. **Refund Requests**
   - Any request for money back, refund, chargeback
   - Action: Escalate to Billing Team
   - Response: "Refund requests are handled by our billing specialists. I'm connecting you now."

3. **Data Breach / Security Incident**
   - Keywords: "hacked", "breach", "data stolen", "unauthorized access"
   - Action: Escalate to Security Team immediately
   - Response: "This is being treated as a priority security matter. Our security team is being notified."

4. **Service Level Agreement (SLA) Violations**
   - Enterprise customers reporting missed SLA
   - Action: Escalate to Account Manager + VP of Customer Success

---

## Standard Escalation (Priority: HIGH)

Escalate after one unsuccessful resolution attempt:

1. **Pricing & Sales Inquiries**
   - Any question about enterprise pricing, custom plans, discounts
   - Reason: "pricing_inquiry"
   - Escalate to: Sales team

2. **Angry / Frustrated Customers**
   - Sentiment score < 0.3
   - Customer uses profanity or aggressive language
   - Customer says "this is unacceptable", "worst service ever"
   - Escalate to: Senior human agent with full conversation context

3. **Account Deletion Requests**
   - GDPR data deletion, full account removal
   - Escalate to: Data Privacy team

4. **Billing Disputes**
   - Incorrect charges, unexpected charges
   - Escalate to: Billing specialists

5. **Technical Issues > 48 hours**
   - Bug reports unresolved for over 48 hours
   - Escalate to: Engineering + Customer Success Manager

---

## Escalation After Exhausting Resources

Escalate when AI cannot resolve after 2 attempts:

1. **Cannot Find Relevant Information**
   - Searched knowledge base twice with different queries
   - No relevant documentation found
   - Escalate with: original query + search attempts

2. **Complex Technical Issues**
   - API integration problems requiring code review
   - Database/performance issues affecting enterprise clients
   - Custom workflow configurations

3. **Customer Explicitly Requests Human**
   - Keywords: "human", "person", "agent", "representative", "real person"
   - WhatsApp: "human", "agent", "help me" (repeated)
   - Immediately escalate

---

## Channel-Specific Escalation Triggers

### WhatsApp
- Customer sends "human" or "agent"
- Customer sends same message 3+ times
- Customer stops responding for 10 minutes then asks again

### Email  
- Customer CC's their manager (indicates urgency)
- Subject line contains "URGENT", "CRITICAL", "ASAP"
- Customer is replying to 3+ previous emails (frustrated pattern)

### Web Form
- Priority selected as "High - Urgent issue"
- Category is "billing" (route to billing team first)

---

## Escalation Information to Include

When escalating, ALWAYS include:
1. Customer ID and contact details
2. Original message and channel
3. Summary of issue
4. What was attempted/found
5. Reason for escalation
6. Sentiment score (if negative)
7. Full conversation history
