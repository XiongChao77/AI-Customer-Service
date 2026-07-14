import './style.css';

// role is fixed for this entry point; the employee dashboard is a
// separate Vite app, not a route on this one. See README for why URL/entry
// point is a demo-only stand-in for real authentication.
const ROLE = 'customer';
const CUSTOMER_ID = 'default';
const API_BASE = 'http://localhost:8000';

const chatLog = document.getElementById('chat-log');
const userInput = document.getElementById('user-input');
const typingIndicator = document.getElementById('typing-indicator');

window.sendMessage = async () => {
    const query = userInput.value.trim();
    if (!query) return;

    appendMessage('user', query, 'You');
    userInput.value = '';
    setTyping(true);

    try {
        const res = await fetch(`${API_BASE}/api/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, role: ROLE, customer_id: CUSTOMER_ID }),
        });

        if (!res.ok) throw new Error(`Server returned ${res.status}`);

        const data = await res.json();
        setTyping(false);

        if (data.handled_by === 'agent') {
            appendMessage('agent', data.response, `Agent #${data.agent_id}`);
        } else {
            appendMessage('bot', data.response, 'Robot');
        }
    } catch (err) {
        setTyping(false);
        appendMessage(
            'bot',
            'Sorry, I could not reach the server. Please check the backend is running and try again.',
            'Robot'
        );
        console.error(err);
    }
};

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') window.sendMessage();
});

function setTyping(isTyping) {
    typingIndicator.classList.toggle('hidden', !isTyping);
}

function appendMessage(type, text, label) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${type}`;

    const labelEl = document.createElement('div');
    labelEl.className = 'sender-label';
    labelEl.innerText = label;

    const textEl = document.createElement('div');
    textEl.className = 'message-text';
    textEl.innerText = text;

    wrapper.appendChild(labelEl);
    wrapper.appendChild(textEl);
    chatLog.appendChild(wrapper);
    chatLog.scrollTop = chatLog.scrollHeight;
}

// Greet on load
appendMessage(
    'bot',
    "Hi! I'm your Lyca assistant. You can ask about your bill, your current plan, changing plans, or enabling roaming.",
    'Robot'
);
