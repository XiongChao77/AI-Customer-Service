"""
FastAPI backend for the AI customer service prototype.

Flow for a customer message:
  1. check_input_safety()          -- reject prompt-injection style input early
  2. classify_intent()             -- structured LLM call -> validated IntentResult
  3. route by intent:
       - account intents (bill/plan/roaming) -> mock data lookup
       - escalate_to_agent         -> scheduling.solve_assignment()
       - out_of_scope / low confidence -> safe fallback, no LLM free-text shown
  4. check_output_safety()         -- final gate before the response leaves the server

This mirrors the layered-guardrail architecture discussed in the interview:
shared model + role-based system prompt/data access, structured output,
schema validation, and a fallback path -- rather than trusting raw LLM
text end-to-end.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import guardrails
import mock_data
from intent_classifier import IntentType, classify_intent
from scheduling import Agent, Ticket, solve_assignment

app = FastAPI(title="Lyca AI Customer Service Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only; restrict to known origins in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory escalation queue for the demo (would be a real queue/DB in prod)
ESCALATION_QUEUE: list[Ticket] = []


class QueryRequest(BaseModel):
    query: str
    role: str = "customer"  # "customer" | "employee" (demo-only distinction;
                             # see README for why this isn't real auth)
    customer_id: str = "default"


class QueryResponse(BaseModel):
    response: str
    handled_by: str  # "ai" | "agent"
    agent_id: str | None = None
    intent: str | None = None
    estimated_wait_minutes: int | None = None


@app.post("/api/query", response_model=QueryResponse)
def handle_query(req: QueryRequest):
    is_safe, reason = guardrails.check_input_safety(req.query)
    if not is_safe:
        return QueryResponse(
            response=guardrails.FALLBACK_MESSAGE,
            handled_by="ai",
            intent="out_of_scope",
        )

    try:
        result = classify_intent(req.query)
    except RuntimeError:
        # e.g. OPENAI_API_KEY not set -- fail safe by routing to a human
        # agent (via the real scheduler) rather than crashing the request.
        return _escalate(req.customer_id, urgency=2, intent="escalate_to_agent")

    if not result.is_safe or result.intent == IntentType.OUT_OF_SCOPE:
        return QueryResponse(
            response=guardrails.FALLBACK_MESSAGE,
            handled_by="ai",
            intent=result.intent.value,
        )

    if result.confidence < 0.5:
        return _escalate(req.customer_id, urgency=1, intent=result.intent.value)

    customer = mock_data.get_customer(req.customer_id)

    if result.intent == IntentType.VIEW_BILL:
        text = (
            f"Your last invoice was {customer['currency']} {customer['last_invoice']['amount']} "
            f"on {customer['last_invoice']['date']} ({customer['last_invoice']['status']})."
        )
        return _safe_response(text, customer, result.intent.value)

    if result.intent == IntentType.VIEW_PLAN:
        text = (
            f"You're currently on {customer['plan']} "
            f"({customer['data_used_gb']}GB / {customer['data_total_gb']}GB used this cycle)."
        )
        return _safe_response(text, customer, result.intent.value)

    if result.intent == IntentType.CHANGE_PLAN:
        plans = mock_data.get_plans()
        names = ", ".join(p["name"] for p in plans)
        text = f"Available plans: {names}. Reply with the plan name to switch."
        return _safe_response(text, customer, result.intent.value)

    if result.intent == IntentType.ENABLE_ROAMING:
        text = "Roaming has been enabled on your line. It may take up to 10 minutes to activate."
        return _safe_response(text, customer, result.intent.value)

    if result.intent == IntentType.GENERAL_QUESTION:
        text = "That's a general question outside your account details -- here's what I know: (demo placeholder)."
        return _safe_response(text, customer, result.intent.value)

    # escalate_to_agent, or anything unhandled
    urgency = 3 if result.intent == IntentType.ESCALATE_TO_AGENT else 1
    return _escalate(req.customer_id, urgency, result.intent.value)


def _safe_response(text: str, customer: dict, intent: str) -> QueryResponse:
    is_safe, reason = guardrails.check_output_safety(text, customer["customer_id"])
    if not is_safe:
        return QueryResponse(response=guardrails.FALLBACK_MESSAGE, handled_by="ai", intent=intent)
    return QueryResponse(response=text, handled_by="ai", intent=intent)


def _escalate(customer_id: str, urgency: int, intent: str) -> QueryResponse:
    ticket_id = f"T{len(ESCALATION_QUEUE) + 1:04d}"
    ESCALATION_QUEUE.append(Ticket(id=ticket_id, urgency=urgency))

    agents = [Agent(**a) for a in mock_data.get_agents()]
    result = solve_assignment(ESCALATION_QUEUE, agents)

    my_assignment = next((a for a in result["assignments"] if a["ticket_id"] == ticket_id), None)

    if my_assignment is None:
        return QueryResponse(
            response="All agents are currently busy. You've been added to the queue.",
            handled_by="ai",
            intent=intent,
        )

    return QueryResponse(
        response=(
            f"I've connected you with Agent #{my_assignment['agent_id']}. "
            f"Estimated wait: {my_assignment['estimated_wait_minutes']} minutes."
        ),
        handled_by="agent",
        agent_id=my_assignment["agent_id"],
        intent=intent,
        estimated_wait_minutes=my_assignment["estimated_wait_minutes"],
    )


@app.get("/api/dashboard")
def get_dashboard():
    """Employee-facing view: current queue, agent roster, and the optimizer's assignment plan."""
    agents = [Agent(**a) for a in mock_data.get_agents()]
    result = solve_assignment(ESCALATION_QUEUE, agents)
    return {
        "queue_length": len(ESCALATION_QUEUE),
        "agents": mock_data.get_agents(),
        "assignments": result["assignments"],
        "total_cost_estimate": result["total_cost"],
        "solver_status": result["solver_status"],
    }


@app.post("/api/dashboard/reset")
def reset_queue():
    """Demo helper to clear the in-memory queue between presentation runs."""
    ESCALATION_QUEUE.clear()
    return {"status": "cleared"}
