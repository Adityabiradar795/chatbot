const BACKEND_URL = "https://chatbot-n5v4.onrender.com";
let isSignUp = false;
let activeSessionId = null;

// ---------- small toast helper (replaces alert()) ----------
let toastTimer = null;
function showToast(text) {
    const toast = document.getElementById("toast");
    toast.innerText = text;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function getToken() {
    return localStorage.getItem("access_token");
}

function checkAuthStatus() {
    const token = getToken();
    const username = localStorage.getItem("username");

    if (token && username) {
        document.getElementById("authModal").style.display = "none";
        document.getElementById("displayUsername").innerText = username;
        document.getElementById("avatarInitial").innerText = username.charAt(0).toUpperCase();
        showWelcomeIfEmpty();
        loadSessions();
    } else {
        document.getElementById("authModal").style.display = "flex";
    }
}

function toggleAuthMode() {
    isSignUp = !isSignUp;
    document.getElementById("authTitle").innerText = isSignUp ? "Sign Up for GenAI" : "Login to GenAI Platform";
    document.getElementById("emailGroup").style.display = isSignUp ? "block" : "none";
    document.getElementById("authSubmitBtn").innerText = isSignUp ? "Sign Up" : "Login";
    document.getElementById("authToggleText").innerText = isSignUp ? "Already have an account? Login" : "Need an account? Sign Up";
}

async function handleAuth() {
    const username = document.getElementById("authUsername").value.trim();
    const password = document.getElementById("authPassword").value.trim();
    const email = document.getElementById("authEmail").value.trim();

    if (!username || !password || (isSignUp && !email)) {
        showToast("Please fill all required fields");
        return;
    }

    const endpoint = isSignUp ? "/register" : "/login";
    const bodyData = isSignUp ? { username, email, password } : { username, password };

    try {
        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(bodyData)
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem("access_token", data.token);
            localStorage.setItem("username", data.username);
            checkAuthStatus();
        } else {
            showToast(data.detail || "Authentication Failed");
        }
    } catch (err) {
        showToast("Could not connect to backend server");
    }
}

function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    activeSessionId = null;
    document.getElementById("historyList").innerHTML = '<div class="history-empty">No conversations yet</div>';
    document.getElementById("chatBox").innerHTML = "";
    checkAuthStatus();
}

// ---------- chat history sidebar ----------
async function loadSessions() {
    const token = getToken();
    if (!token) return;

    try {
        const response = await fetch(`${BACKEND_URL}/sessions`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) return;

        const sessions = await response.json();
        const list = document.getElementById("historyList");

        if (!sessions.length) {
            list.innerHTML = '<div class="history-empty">No conversations yet</div>';
            return;
        }

        list.innerHTML = "";
        sessions.forEach(s => {
            const item = document.createElement("div");
            item.className = "history-item" + (s.id === activeSessionId ? " active" : "");

            const title = document.createElement("span");
            title.className = "history-item-title";
            title.innerText = s.title || "Untitled chat";
            title.onclick = () => loadSessionMessages(s.id);

            const delBtn = document.createElement("button");
            delBtn.className = "history-delete-btn";
            delBtn.innerText = "✕";
            delBtn.title = "Delete conversation";
            delBtn.onclick = (e) => {
                e.stopPropagation();
                deleteSession(s.id);
            };

            item.appendChild(title);
            item.appendChild(delBtn);
            list.appendChild(item);
        });
    } catch (err) {
        // silent fail — sidebar just stays as-is
    }
}

async function loadSessionMessages(sessionId) {
    const token = getToken();

    try {
        const response = await fetch(`${BACKEND_URL}/sessions/${sessionId}/messages`, {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) {
            showToast("Could not load that conversation");
            return;
        }

        const msgs = await response.json();
        activeSessionId = sessionId;

        const chatBox = document.getElementById("chatBox");
        chatBox.innerHTML = "";

        if (!msgs.length) {
            appendMessage("New conversation started. How can I help you?", "bot", true);
        } else {
            msgs.forEach(m => appendMessage(m.content, m.sender === "user" ? "user" : "bot", true));
        }

        highlightActiveSession();
    } catch (err) {
        showToast("Could not connect to backend server");
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Delete this conversation? This can't be undone.")) return;

    const token = getToken();

    try {
        const response = await fetch(`${BACKEND_URL}/sessions/${sessionId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) {
            showToast("Could not delete conversation");
            return;
        }

        if (sessionId === activeSessionId) {
            startNewChat();
        }

        loadSessions();
    } catch (err) {
        showToast("Could not connect to backend server");
    }
}

function highlightActiveSession() {
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
    loadSessions();
}

function showWelcomeIfEmpty() {
    const chatBox = document.getElementById("chatBox");
    if (!chatBox.children.length) {
        appendMessage("Hello! Welcome to your secure AI assistant. How can I help you today?", "bot", true);
    }
}

// ---------- chat ----------
async function sendMessage() {
    const inputElement = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const systemPrompt = document.getElementById("systemPrompt").value.trim();
    const messageText = inputElement.value.trim();

    if (!messageText) return;

    appendMessage(messageText, "user", false);
    inputElement.value = "";
    sendBtn.disabled = true;

    const loadingId = appendTyping();
    const token = getToken();

    let fullText = "";
    let streamStarted = false;

    try {
        const response = await fetch(`${BACKEND_URL}/chat/stream`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({
                user_input: messageText,
                system_prompt: systemPrompt,
                session_id: activeSessionId
            })
        });

        if (response.status === 401) {
            showToast("Session expired — please log in again");
            logout();
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split("\n\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const data = JSON.parse(line.replace("data: ", ""));

                if (data.type === "session") {
                    activeSessionId = data.session_id;
                } else if (data.type === "token") {
                    if (!streamStarted) {
                        streamStarted = true;
                        convertTypingToBubble(loadingId);
                    }
                    fullText += data.token;
                    const bubble = document.querySelector(`#${loadingId} .message`);
                    if (bubble) {
                        bubble.innerHTML = marked.parse(fullText);
                        const chatBox = document.getElementById("chatBox");
                        chatBox.scrollTop = chatBox.scrollHeight;
                    }
                } else if (data.type === "done") {
                    loadSessions();
                }
            }
        }
    } catch (error) {
        const bubble = document.querySelector(`#${loadingId} .message`);
        if (bubble) {
            bubble.innerText = "Error: Connection lost or stream failed.";
            bubble.style.color = "#f43f5e";
        }
    } finally {
        sendBtn.disabled = false;
    }
}

function appendMessage(text, role, isMarkdown) {
    const chatBox = document.getElementById("chatBox");
    const row = document.createElement("div");
    const uniqueId = "msg-" + Date.now() + "-" + Math.random().toString(36).substring(2, 7);

    row.id = uniqueId;
    row.className = `msg-row ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.innerText = role === "user" ? "U" : "✦";

    const bubble = document.createElement("div");
    bubble.className = "message";

    if (isMarkdown && typeof marked !== "undefined") {
        bubble.innerHTML = marked.parse(text);
    } else {
        bubble.innerText = text;
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;

    return uniqueId;
}

function appendTyping() {
    const chatBox = document.getElementById("chatBox");
    const row = document.createElement("div");
    const uniqueId = "msg-" + Date.now() + "-" + Math.random().toString(36).substring(2, 7);

    row.id = uniqueId;
    row.className = "msg-row bot";
    row.innerHTML = `
        <div class="msg-avatar">✦</div>
        <div class="message"><div class="typing-dots"><span></span><span></span><span></span></div></div>
    `;

    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;
    return uniqueId;
}

function convertTypingToBubble(id) {
    const bubble = document.querySelector(`#${id} .message`);
    if (bubble) bubble.innerHTML = "";
}

function startNewChat() {
    activeSessionId = null;
    document.getElementById("chatBox").innerHTML = "";
    appendMessage("New conversation started. How can I help you?", "bot", true);
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
}

function handleKeyPress(e) {
    if (e.key === "Enter") sendMessage();
}

checkAuthStatus();
