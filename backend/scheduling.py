"""
Agent assignment / scheduling optimization using OR-Tools CP-SAT.

Problem framing:
  Given a set of escalated tickets (each with an urgency weight) and a
  roster of available agents (each with a skill level -> handling speed,
  and an hourly cost), assign tickets to agents so that:
    1. total (urgency-weighted) estimated wait time is minimized, AND
    2. the cost of the agents used is taken into account,
  subject to each agent having a maximum concurrent ticket capacity.

This is a small, demo-scale version of the kind of constraint model a real
workforce-scheduling system would use. It's intentionally the same tool
(CP-SAT) referenced in the interview, applied to Lyca's actual stated need:
"identify human agent requests, schedule based on current agent workload,
tell the customer the wait time, minimize cost."
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model


@dataclass
class Ticket:
    id: str
    urgency: int  # 1 (low) - 3 (high)


@dataclass
class Agent:
    id: str
    name: str
    skill_level: int  # 1-3, higher = faster resolution
    hourly_cost: float
    capacity: int = 2  # max concurrent tickets this shift


BASE_HANDLE_MINUTES = 12  # baseline time to resolve one ticket at skill_level 1


def estimated_handle_minutes(agent: Agent) -> int:
    # Higher skill -> proportionally faster. Kept integer for CP-SAT.
    return max(3, round(BASE_HANDLE_MINUTES / agent.skill_level))


def solve_assignment(tickets: list[Ticket], agents: list[Agent]) -> dict:
    model = cp_model.CpModel()

    n_tickets = len(tickets)
    n_agents = len(agents)

    if n_tickets == 0 or n_agents == 0:
        return {"assignments": [], "total_cost": 0, "solver_status": "no_op"}

    handle_time = [estimated_handle_minutes(a) for a in agents]

    # x[i][j] = 1 if ticket i is assigned to agent j
    x = {}
    for i in range(n_tickets):
        for j in range(n_agents):
            x[i, j] = model.NewBoolVar(f"x_{i}_{j}")

    # Each ticket assigned to exactly one agent
    for i in range(n_tickets):
        model.Add(sum(x[i, j] for j in range(n_agents)) == 1)

    # Each agent can't exceed capacity
    for j, agent in enumerate(agents):
        model.Add(sum(x[i, j] for i in range(n_tickets)) <= agent.capacity)

    # Objective: minimize urgency-weighted handle time + a cost term.
    # cost_weight controls how much we trade agent cost against speed;
    # tuned low here since correctness/wait-time matters more than the
    # last dollar in a customer-facing queue, but it's a knob a real system
    # would expose to ops.
    cost_weight = 2
    objective_terms = []
    for i, ticket in enumerate(tickets):
        for j, agent in enumerate(agents):
            weighted_time = ticket.urgency * handle_time[j]
            cost_term = round(cost_weight * agent.hourly_cost / 10)
            objective_terms.append((weighted_time + cost_term) * x[i, j])

    model.Minimize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"assignments": [], "total_cost": 0, "solver_status": "infeasible"}

    # Build per-agent queues to compute cumulative wait time per ticket
    assignments = []
    agent_queue_minutes = {j: 0 for j in range(n_agents)}
    total_cost = 0.0

    for j, agent in enumerate(agents):
        assigned = [i for i in range(n_tickets) if solver.Value(x[i, j]) == 1]
        # higher urgency first within an agent's queue
        assigned.sort(key=lambda i: -tickets[i].urgency)

        running_wait = 0
        for i in assigned:
            wait_time = running_wait
            running_wait += handle_time[j]
            assignments.append({
                "ticket_id": tickets[i].id,
                "agent_id": agent.id,
                "agent_name": agent.name,
                "estimated_wait_minutes": wait_time,
                "estimated_handle_minutes": handle_time[j],
            })
            total_cost += agent.hourly_cost * (handle_time[j] / 60)

    return {
        "assignments": assignments,
        "total_cost": round(total_cost, 2),
        "solver_status": solver.StatusName(status),
    }
