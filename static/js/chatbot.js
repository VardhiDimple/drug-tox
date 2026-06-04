/**
 * DRUG TOX PRO — Floating AI Assistant
 */

const CHAT_STORAGE_KEY = "drugtoxpro_chat_history";

const PANEL_LABELS = {
  home: "Home",
  admet: "ADMET Predictor",
  viewer: "Molecular Viewer",
  ml: "ML Classifier",
  viz: "Visualization",
  go: "GO Enrichment",
  disease: "Disease Prediction",
  about: "About",
};

let chatHistory = [];
let chatOpen = false;

function loadChatHistory() {
  try {
    const raw = sessionStorage.getItem(CHAT_STORAGE_KEY);
    chatHistory = raw ? JSON.parse(raw) : [];
  } catch {
    chatHistory = [];
  }
}

function saveChatHistory() {
  sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(chatHistory.slice(-40)));
}

function buildChatContext() {
  const panel = window.appContext?.getPanel?.() || "home";
  const ml = window.appContext?.getMlContext?.() || {};
  const viz = window.appContext?.getVizContext?.() || {};
  const lastError = window.appContext?.getLastError?.() || null;

  return {
    panel,
    columns: ml.columns || viz.columns || [],
    column_stats: ml.column_stats || {},
    numeric_columns: ml.numeric_columns || viz.numeric_columns || [],
    categorical_columns: ml.categorical_columns || viz.categorical_columns || [],
    target_column: ml.target_column || null,
    last_error: lastError,
  };
}

function formatReply(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function renderMessages() {
  const box = document.getElementById("chatbot-messages");
  if (!box) return;
  if (!chatHistory.length) {
    box.innerHTML = `<div class="chat-msg bot"><p>Hi! I'm your DRUG TOX PRO assistant. Ask me anything or use the quick actions below.</p></div>`;
    return;
  }
  box.innerHTML = chatHistory.map((m) =>
    `<div class="chat-msg ${m.role === "user" ? "user" : "bot"}"><p>${m.role === "user" ? m.content : formatReply(m.content)}</p></div>`
  ).join("");
  box.scrollTop = box.scrollHeight;
}

async function renderSuggestions() {
  const wrap = document.getElementById("chatbot-suggestions");
  if (!wrap) return;
  let questions = [];
  try {
    const json = await (await fetch("/api/chat/suggestions")).json();
    if (json.success) questions = json.data;
  } catch {
    questions = [
      "How do I use ADMET Predictor?",
      "What is a SMILES string?",
      "How do I train an ML model?",
    ];
  }
  wrap.innerHTML = questions.map((q) =>
    `<button type="button" class="chat-suggestion-btn" data-q="${q.replace(/"/g, "&quot;")}">${q}</button>`
  ).join("");
  wrap.querySelectorAll(".chat-suggestion-btn").forEach((btn) => {
    btn.addEventListener("click", () => sendMessage(btn.dataset.q));
  });
}

function updatePanelLabel() {
  const el = document.getElementById("chatbot-panel-label");
  const panel = window.appContext?.getPanel?.() || "home";
  if (el) el.textContent = PANEL_LABELS[panel] ? ` · ${PANEL_LABELS[panel]}` : "";
}

function openChat() {
  chatOpen = true;
  document.getElementById("chatbot-window")?.classList.remove("hidden");
  document.getElementById("chatbot-toggle")?.classList.add("hidden");
  updatePanelLabel();
  renderMessages();
  renderSuggestions();
  document.getElementById("chatbot-input")?.focus();
}

function closeChat() {
  chatOpen = false;
  document.getElementById("chatbot-window")?.classList.add("hidden");
  document.getElementById("chatbot-toggle")?.classList.remove("hidden");
}

function minimizeChat() {
  closeChat();
}

async function sendMessage(text) {
  const message = (text || "").trim();
  if (!message) return;

  const input = document.getElementById("chatbot-input");
  if (input) input.value = "";

  chatHistory.push({ role: "user", content: message });
  renderMessages();
  saveChatHistory();

  const box = document.getElementById("chatbot-messages");
  const loading = document.createElement("div");
  loading.className = "chat-msg bot chat-loading";
  loading.innerHTML = "<p>Thinking…</p>";
  box?.appendChild(loading);
  box.scrollTop = box.scrollHeight;

  try {
    const json = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        context: buildChatContext(),
        history: chatHistory.slice(-10),
      }),
    }).then((r) => r.json());

    loading.remove();

    if (!json.success) {
      chatHistory.push({ role: "assistant", content: json.error || "Sorry, something went wrong." });
    } else {
      chatHistory.push({ role: "assistant", content: json.data.reply });
      if (json.data.suggested_questions?.length) {
        const wrap = document.getElementById("chatbot-suggestions");
        if (wrap) {
          wrap.innerHTML = json.data.suggested_questions.map((q) =>
            `<button type="button" class="chat-suggestion-btn" data-q="${q.replace(/"/g, "&quot;")}">${q}</button>`
          ).join("");
          wrap.querySelectorAll(".chat-suggestion-btn").forEach((btn) => {
            btn.addEventListener("click", () => sendMessage(btn.dataset.q));
          });
        }
      }
    }
  } catch {
    loading.remove();
    chatHistory.push({
      role: "assistant",
      content: "Could not reach the assistant. Please check your connection and try again.",
    });
  }

  renderMessages();
  saveChatHistory();
}

function initChatbot() {
  loadChatHistory();

  document.getElementById("chatbot-toggle")?.addEventListener("click", openChat);
  document.getElementById("chatbot-close")?.addEventListener("click", closeChat);
  document.getElementById("chatbot-minimize")?.addEventListener("click", minimizeChat);

  document.getElementById("chatbot-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    sendMessage(document.getElementById("chatbot-input")?.value);
  });

  window.addEventListener("panelchange", updatePanelLabel);
  updatePanelLabel();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChatbot);
} else {
  initChatbot();
}
