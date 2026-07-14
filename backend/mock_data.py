"""
Mock data layer.
In production this would be replaced by real billing/CRM/HR system integrations.
"""

MOCK_CUSTOMERS = {
    "default": {
        "customer_id": "C10293",
        "name": "Alex Chen",
        "plan": "Lyca International 20GB",
        "monthly_price": 20.00,
        "currency": "AED",
        "data_used_gb": 14.2,
        "data_total_gb": 20,
        "roaming_enabled": False,
        "billing_cycle_end": "2026-07-31",
        "last_invoice": {
            "amount": 20.00,
            "date": "2026-06-30",
            "status": "paid",
        },
    }
}

AVAILABLE_PLANS = [
    {"id": "P1", "name": "Lyca Basic 5GB", "price": 10.00},
    {"id": "P2", "name": "Lyca International 20GB", "price": 20.00},
    {"id": "P3", "name": "Lyca Unlimited 50GB", "price": 35.00},
]

# Simplified agent roster for the scheduling / cost optimization demo.
# skill_level roughly maps to how fast an agent can resolve a ticket.
AGENTS = [
    {"id": "101", "name": "Agent 101", "skill_level": 3, "hourly_cost": 25},
    {"id": "102", "name": "Agent 102", "skill_level": 2, "hourly_cost": 18},
    {"id": "103", "name": "Agent 103", "skill_level": 3, "hourly_cost": 25},
    {"id": "104", "name": "Agent 104", "skill_level": 1, "hourly_cost": 14},
]


def get_customer(customer_id: str = "default"):
    return MOCK_CUSTOMERS.get(customer_id, MOCK_CUSTOMERS["default"])


def get_plans():
    return AVAILABLE_PLANS


def get_agents():
    return AGENTS
