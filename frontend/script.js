// 1. Dynamic API Fallback URLs List
const API_BASE_URLS = [
    window.location.origin.startsWith("http") ? window.location.origin : null,
    "http://localhost:8000",
    "http://127.0.0.1:8000"
].filter(Boolean);

// DOM Elements & Application State
const chatBody = document.getElementById("chat-body");
const messageInput = document.getElementById("message");
const sendBtn = document.getElementById("send-btn");
let loading = false;
const CHAT_SESSION_ID = sessionStorage.getItem("kb-chat-session")
    || (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`);
sessionStorage.setItem("kb-chat-session", CHAT_SESSION_ID);

/* ------------------------ */

// Helper: Get formatted short timestamps
function getTime() {
    return new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit"
    });
}

// Helper: Ensure the view tracks to the latest text message
function scrollBottom() {
    chatBody.scrollTop = chatBody.scrollHeight;
}

/* ------------------------ */

// Window Controls
function toggleChat() {
    const chat = document.getElementById("chat-window");
    chat.style.display = chat.style.display === "flex" ? "none" : "flex";
}

function toggleFull() {
    document.getElementById("chat-window").classList.toggle("fullscreen");
}

/* ------------------------ */

// Unified Messaging Component
function addMessage(sender, text) {
    const wrapper = document.createElement("div");
    // Maps "You" to 'user' class and everything else to 'ai' class
    const roleClass = sender === "You" ? "user" : "ai";
    wrapper.className = `message ${roleClass}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    // Use marked library rendering engine for AI responses; parse as safe text for user inputs
    if (sender !== "You") {
        bubble.className += " markdown-body";
        bubble.innerHTML = DOMPurify.sanitize(marked.parse(text));
    } else {
        bubble.textContent = text;
    }

    // Embed the calculated dynamic timeline stamp
    const timestamp = document.createElement("div");
    timestamp.className = "timestamp";
    timestamp.textContent = getTime();

    bubble.appendChild(timestamp);
    wrapper.appendChild(bubble);
    chatBody.appendChild(wrapper);

    scrollBottom();
}

function addArticleLinks(bubble, articles, apiBaseUrl = window.location.origin) {
    if (!Array.isArray(articles) || articles.length === 0) return;

    const section = document.createElement("div");
    section.className = "kb-suggestions";

    const heading = document.createElement("div");
    heading.className = "kb-suggestions-title";
    heading.textContent = "Suggested KB articles";
    section.appendChild(heading);

    articles.forEach((article) => {
        const row = document.createElement("div");
        row.className = "kb-suggestion";

        const label = document.createElement("span");
        label.className = "kb-suggestion-label";
        label.textContent = article.kb_id && article.kb_id !== "NOT AVAILABLE"
            ? article.kb_id
            : article.source;

        const actions = document.createElement("span");
        actions.className = "kb-suggestion-actions";
        const encodedSource = encodeURIComponent(article.source);

        const viewLink = document.createElement("a");
        viewLink.href = article.view_url || `${apiBaseUrl}/kb/${encodedSource}`;
        viewLink.target = "_blank";
        viewLink.rel = "noopener noreferrer";
        viewLink.textContent = "View";

        const downloadLink = document.createElement("a");
        downloadLink.href = article.download_url
            || `${apiBaseUrl}/kb/${encodedSource}?download=true`;
        downloadLink.setAttribute("download", "");
        downloadLink.textContent = "Download";

        actions.append(viewLink, downloadLink);
        row.append(label, actions);
        section.appendChild(row);
    });

    bubble.appendChild(section);
}

/* ------------------------ */

// Typing State Mechanics
function showTyping() {
    // Prevent creating duplicate indicators
    if (document.getElementById("typing")) return;

    const typing = document.createElement("div");
    typing.className = "message ai";
    typing.id = "typing";

    typing.innerHTML = `
        <div class="bubble">
            <div class="typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    chatBody.appendChild(typing);
    scrollBottom();
}

function removeTyping() {
    document.getElementById("typing")?.remove();
}

/* ------------------------ */

// Network Request Engine with URL Switching & Timeouts
async function typeAIMessage(text, articles = [], apiBaseUrl = window.location.origin) {
    const wrapper = document.createElement("div");
    wrapper.className = "message ai";

    const bubble = document.createElement("div");
    bubble.className = "bubble markdown-body";

    wrapper.appendChild(bubble);
    chatBody.appendChild(wrapper);

    let current = "";

    for (const char of text) {
        current += char;
        bubble.innerHTML = DOMPurify.sanitize(marked.parse(current));
        scrollBottom();
        await new Promise(resolve => setTimeout(resolve, 10));
    }

    addArticleLinks(bubble, articles, apiBaseUrl);

    const timestamp = document.createElement("div");
    timestamp.className = "timestamp";
    timestamp.textContent = getTime();

    bubble.appendChild(timestamp);
}
async function sendMessage() {
    if (loading) return;

    const text = messageInput.value.trim();
    if (!text) return;

    // Instantly append user text and clear up input container
    addMessage("You", text);
    messageInput.value = "";
    
    loading = true;
    showTyping();

    // Enforce 5-minute processing limit (300,000 ms) using AbortController
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000);

    try {
        let response = null;
        let responseBaseUrl = null;
        let lastError = null;

        // Loop through endpoints until a working server connection is found
        for (const apiBaseUrl of API_BASE_URLS) {
            try {
                const res = await fetch(`${apiBaseUrl}/ask`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        query: text,
                        session_id: CHAT_SESSION_ID
                    }),
                    signal: controller.signal
                });

                // Failover immediately if endpoint configuration configuration is wrong
                if (res.status === 404 || res.status === 405) {
                    lastError = new Error(`${apiBaseUrl} does not expose /ask`);
                    continue;
                }

                response = res;
                responseBaseUrl = apiBaseUrl;
                break; // Working URL discovered, break the sequence loop
            } catch (err) {
                lastError = err; // Save connection issues and move to next URL
            }
        }

        if (!response) {
            throw lastError || new Error("API not reachable");
        }

        // Process HTTP operational errors returned by the server
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API Error (${response.status})`);
        }

        const data = await response.json();
        removeTyping();
        await typeAIMessage(
            data.answer || "No response received.",
            data.articles,
            responseBaseUrl
        );

    } catch (err) {
        removeTyping();

        let errorMessage = "API not reachable";
        if (err.name === "AbortError") {
            errorMessage = "The request timed out. Please try again.";
        } else if (err.message) {
            errorMessage = err.message;
        }

        // Format and append error notice into user interface layout
        await typeAIMessage(`❌ **Error**\n\n${errorMessage}`);
        
        console.error(err);
    } finally {
        clearTimeout(timeoutId);
        loading = false;
    }
}

/* ------------------------ */

// Application Bootstrap and DOM Bindings
document.addEventListener("DOMContentLoaded", () => {
    
    // Attach Bubble and Close Widget Actions
    document.getElementById("chat-bubble")?.addEventListener("click", toggleChat);
    document.getElementById("close-btn")?.addEventListener("click", toggleChat);
    document.getElementById("fullscreen-btn")?.addEventListener("click", toggleFull);

    // Messaging Triggers
    sendBtn?.addEventListener("click", sendMessage);
    messageInput?.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            sendMessage();
        }
    });

    // Run custom greeting message on load completion
    addMessage(
        "AI",
        `# 👋 Welcome\n\nI'm your AI Support Assistant.\n\nYou can ask me:\n- Incident troubleshooting\n- Root Cause Analysis\n- Knowledge Base Articles\n- Historical Ticket Search\n- Resolution Recommendations\n\nHow can I help today?`
    );
});
