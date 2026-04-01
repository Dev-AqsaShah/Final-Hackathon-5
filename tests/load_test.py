"""
Stage 3: Load Test — TechNova Customer Success FTE
Uses Locust to simulate multi-channel traffic.

Run:
    pip install locust
    locust -f tests/load_test.py --host http://localhost:8002
    Then open http://localhost:8089 in browser
"""

from locust import HttpUser, task, between
import random
import string


def rand_email():
    tag = ''.join(random.choices(string.ascii_lowercase, k=8))
    return f"loadtest_{tag}@example.com"


def rand_name():
    first = random.choice(["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace"])
    last  = random.choice(["Smith", "Johnson", "Lee", "Patel", "Kim", "Garcia"])
    return f"{first} {last}"


CATEGORIES = ["general", "technical", "billing", "feedback", "bug_report"]
PRIORITIES  = ["low", "medium", "high"]

MESSAGES = [
    "I cannot log into my account even after resetting my password multiple times.",
    "The API is returning a 500 error on the analytics endpoint when I query more than 90 days.",
    "I was charged twice this month and would like a clarification on my invoice.",
    "How do I export my data to CSV format? I cannot find the option in settings.",
    "The dashboard is loading very slowly — takes more than 30 seconds every time.",
    "I need to upgrade my plan to Enterprise. Can you help me with the process?",
    "Two-factor authentication is not sending the SMS code to my phone number.",
    "The webhook integration is not firing events when a new user signs up.",
    "I accidentally deleted some data. Is there a way to recover it?",
    "Your mobile app crashes immediately when I try to open the reports section.",
]


class WebFormUser(HttpUser):
    """
    Simulates users submitting support tickets via the web form.
    This is the most common channel (weight=3).
    """
    wait_time = between(2, 8)
    weight = 3

    @task(5)
    def submit_support_form(self):
        self.client.post("/support/submit", json={
            "name":     rand_name(),
            "email":    rand_email(),
            "subject":  f"Support request #{random.randint(1000, 9999)}",
            "category": random.choice(CATEGORIES),
            "priority": random.choice(PRIORITIES),
            "message":  random.choice(MESSAGES),
        })

    @task(2)
    def check_ticket_status(self):
        # Submit first, then check status
        res = self.client.post("/support/submit", json={
            "name":    rand_name(),
            "email":   rand_email(),
            "subject": "Ticket status check test",
            "category": "general",
            "message": "Checking if ticket status retrieval works under load.",
        })
        if res.status_code == 200:
            ticket_id = res.json().get("ticket_id")
            if ticket_id:
                self.client.get(f"/support/ticket/{ticket_id}")

    @task(1)
    def submit_high_priority(self):
        self.client.post("/support/submit", json={
            "name":     rand_name(),
            "email":    rand_email(),
            "subject":  "URGENT: Production system is down",
            "category": "technical",
            "priority": "high",
            "message":  "Our production system is completely down. All users are affected.",
        })


class HealthMonitorUser(HttpUser):
    """
    Simulates monitoring/health check traffic.
    Represents uptime monitors and metrics scrapers (weight=1).
    """
    wait_time = between(5, 15)
    weight = 1

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(1)
    def metrics_check(self):
        self.client.get("/metrics/channels")


class APIExplorerUser(HttpUser):
    """
    Simulates users using the API to look up customers.
    Lower frequency (weight=1).
    """
    wait_time = between(10, 30)
    weight = 1

    @task
    def lookup_customer(self):
        email = rand_email()
        self.client.get("/customers/lookup", params={"email": email})
