let ws;
let token;
let currentUsername;
let wsConnectionId = 0;  // Track connection instances to prevent stale messages

document.addEventListener('DOMContentLoaded', () => {
    // Check if we have persistent credential tokens stored
    const savedToken = localStorage.getItem('dchat_token');
    const savedUser = localStorage.getItem('dchat_user');
    if (savedToken && savedUser) {
        token = savedToken;
        currentUsername = savedUser;
        showChat();
    }
});

function showError(msg) {
    const errDiv = document.getElementById('auth-error');
    errDiv.innerText = msg;
    setTimeout(() => { errDiv.innerText = ''; }, 4000);
}

async function register() {
    const un = document.getElementById('username').value.trim();
    const pw = document.getElementById('password').value.trim();
    if (!un || !pw) return showError("Please enter both username and password.");

    document.querySelector('.btn.secondary').innerText = "Working...";

    try {
        const res = await fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: un, password: pw })
        });

        if (res.ok) {
            showError('Registered successfully! You can now login.');
            document.getElementById('auth-error').style.color = '#10B981'; // green

            // Automatically login after successful registration (optional)
            // await login();
        } else {
            const data = await res.json();
            showError(data.detail || 'Registration failed.');
            document.getElementById('auth-error').style.color = 'var(--error)';
        }
    } catch (e) {
        showError('Network error connecting to the server.');
    } finally {
        document.querySelector('.btn.secondary').innerText = "Register";
    }
}

async function login() {
    const un = document.getElementById('username').value.trim();
    const pw = document.getElementById('password').value.trim();
    if (!un || !pw) return showError("Please enter both username and password.");

    document.querySelector('.btn.primary').innerText = "Logging in...";

    try {
        const res = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: un, password: pw })
        });

        if (res.ok) {
            token = btoa(un + ':' + pw);
            currentUsername = un;

            // Persist the session
            localStorage.setItem('dchat_token', token);
            localStorage.setItem('dchat_user', un);

            showChat();
        } else {
            const data = await res.json();
            showError(data.detail || 'Invalid credentials.');
            document.getElementById('auth-error').style.color = 'var(--error)';
        }
    } catch (e) {
        showError('Network error connecting to the server.');
    } finally {
        document.querySelector('.btn.primary').innerText = "Login";
    }
}

function logout() {
    localStorage.removeItem('dchat_token');
    localStorage.removeItem('dchat_user');
    if (ws) ws.close();

    document.getElementById('auth').style.display = 'flex';
    document.getElementById('chat').style.display = 'none';
    document.getElementById('messages').innerHTML = ''; // clear msgs
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
}

function showChat() {
    document.getElementById('auth').style.display = 'none';
    document.getElementById('chat').style.display = 'flex';

    const indicator = document.querySelector('.status-indicator');
    indicator.style.backgroundColor = '#F59E0B'; // yellow (connecting)

    loadHistory();
    connectWs();
}

async function loadHistory() {
    try {
        const res = await fetch('/history');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('messages').innerHTML = ''; // Clear stale UI msgs first
            data.messages.forEach(m => appendMsg(m));
        }
    } catch (e) {
        console.error("Failed to fetch history", e);
    }
}

function connectWs() {
    // Close old connection if it exists
    if (ws) {
        ws.close();
        // Don't process messages from this old connection
        wsConnectionId++;
    }

    // Create new connection
    const currentConnId = ++wsConnectionId;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(protocol + '//' + location.host + '/ws');

    ws.onopen = () => {
        // Only send if this is still the current connection
        if (wsConnectionId === currentConnId) {
            ws.send(token); // Send auth token initially to authenticate the stream
            document.querySelector('.status-indicator').style.backgroundColor = '#10B981'; // Green (connected)
        }
    };

    ws.onmessage = (event) => {
        // Ignore messages from stale connections
        if (wsConnectionId !== currentConnId) return;

        try {
            const data = JSON.parse(event.data);
            appendMsg(data);
        } catch (e) {
            console.error("Failed parsing message:", event.data);
        }
    };

    ws.onclose = () => {
        // Only update UI if this is the current connection
        if (wsConnectionId === currentConnId) {
            document.querySelector('.status-indicator').style.backgroundColor = '#EF4444'; // Red (disconnected)
            // Auto-reconnect purely as UX polish
            setTimeout(() => {
                if (localStorage.getItem('dchat_token') && wsConnectionId === currentConnId) {
                    connectWs();
                }
            }, 5000);
        }
    };

    ws.onerror = (err) => {
        // Only log if this is the current connection
        if (wsConnectionId === currentConnId) {
            console.error("WebSocket error:", err);
        }
    };
}

function formatTime(timestamp) {
    if (!timestamp) return "";
    const date = new Date(parseInt(timestamp) * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function appendMsg(data) {
    const msgs = document.getElementById('messages');

    const isSelf = data.sender === currentUsername;

    const div = document.createElement('div');
    div.className = `msg ${isSelf ? 'self' : 'other'}`;

    const metaHtml = isSelf
        ? `<div class="meta">${formatTime(data.timestamp)}</div>`
        : `<div class="meta">${data.sender}&nbsp;&nbsp;&bull;&nbsp;&nbsp;${formatTime(data.timestamp)}</div>`;

    div.innerHTML = `
        ${metaHtml}
        <div class="bubble">${data.message}</div>
    `;

    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        const input = document.getElementById('msgInput');
        if (input.value.trim() !== '') {
            sendMsg();
        }
    }
}

function sendMsg() {
    const input = document.getElementById('msgInput');
    const msgTest = input.value.trim();
    if (msgTest && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(msgTest);
        input.value = '';
        input.focus();
    }
}
