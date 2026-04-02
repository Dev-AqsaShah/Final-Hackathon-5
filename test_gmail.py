from dotenv import load_dotenv
load_dotenv('production/.env')
from production.channels.gmail_handler import GmailHandler
import asyncio

h = GmailHandler()
result = asyncio.run(h.send_reply(
    'aqsashah8802@gmail.com',
    'TechNova Support Response',
    'Dear Customer, Thank you for contacting TechNova Support. Your issue has been received and our AI agent is processing it. Ticket ID: TKT-DEMO-001. Best regards, TechNova AI Support Team'
))
print('Email sent:', result)
