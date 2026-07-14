import './style.css';

const API_BASE = 'http://localhost:8000';

window.refreshDashboard = loadDashboard;
window.resetQueue = async () => {
    await fetch(`${API_BASE}/api/dashboard/reset`, { method: 'POST' });
    loadDashboard();
};

async function loadDashboard() {
    const statusLine = document.getElementById('status-line');
    statusLine.innerText = 'Loading...';

    try {
        const res = await fetch(`${API_BASE}/api/dashboard`);
        if (!res.ok) throw new Error(`Server returned ${res.status}`);
        const data = await res.json();

        renderSummary(data);
        renderAgentTable(data.agents, data.assignments);
        renderAssignmentTable(data.assignments);

        statusLine.innerText = `Solver status: ${data.solver_status} | Updated ${new Date().toLocaleTimeString()}`;
    } catch (err) {
        statusLine.innerText = 'Could not reach backend. Is it running on :8000?';
        console.error(err);
    }
}

function renderSummary(data) {
    const grid = document.getElementById('summary-grid');
    grid.innerHTML = '';

    const cards = [
        { label: 'Tickets in Queue', value: data.queue_length },
        { label: 'Agents on Shift', value: data.agents.length },
        { label: 'Est. Total Cost (AED)', value: data.total_cost_estimate },
        {
            label: 'Avg Wait (min)',
            value: avgWait(data.assignments),
        },
    ];

    cards.forEach((c) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `<h4>${c.label}</h4><p>${c.value}</p>`;
        grid.appendChild(card);
    });
}

function avgWait(assignments) {
    if (!assignments || assignments.length === 0) return 0;
    const total = assignments.reduce((sum, a) => sum + a.estimated_wait_minutes, 0);
    return Math.round((total / assignments.length) * 10) / 10;
}

function renderAgentTable(agents, assignments) {
    const container = document.getElementById('agent-table');

    const rows = agents
        .map((agent) => {
            const load = assignments.filter((a) => a.agent_id === agent.id).length;
            const loadClass = load === 0 ? 'idle' : load >= 2 ? 'busy' : 'active';
            return `
                <tr>
                    <td>${agent.name}</td>
                    <td>Skill ${agent.skill_level}</td>
                    <td>AED ${agent.hourly_cost}/hr</td>
                    <td><span class="pill ${loadClass}">${load} ticket(s)</span></td>
                </tr>
            `;
        })
        .join('');

    container.innerHTML = `
        <table>
            <thead>
                <tr><th>Agent</th><th>Skill</th><th>Cost</th><th>Current Load</th></tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderAssignmentTable(assignments) {
    const container = document.getElementById('assignment-table');

    if (!assignments || assignments.length === 0) {
        container.innerHTML = '<p class="empty-state">No tickets in queue right now.</p>';
        return;
    }

    const rows = assignments
        .map(
            (a) => `
                <tr>
                    <td>${a.ticket_id}</td>
                    <td>Agent #${a.agent_id}</td>
                    <td>${a.estimated_wait_minutes} min</td>
                    <td>${a.estimated_handle_minutes} min</td>
                </tr>
            `
        )
        .join('');

    container.innerHTML = `
        <table>
            <thead>
                <tr><th>Ticket</th><th>Assigned Agent</th><th>Est. Wait</th><th>Est. Handle Time</th></tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

loadDashboard();
setInterval(loadDashboard, 8000);
