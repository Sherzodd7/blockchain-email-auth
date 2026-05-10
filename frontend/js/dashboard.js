// frontend/js/dashboard.js — исправленная версия для SPA

async function checkStatusDashboard() {
  try {
    const r = await fetch(`${API}/health`);
    const d = await r.json();
    const dot  = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    dot.className   = d.blockchain.includes("connected")
      ? "status-dot online" : "status-dot";
    text.textContent = d.blockchain.includes("connected")
      ? "Blockchain online" : "Mock mode (Ganache offline)";
  } catch {
    document.getElementById("statusDot").className = "status-dot offline";
    document.getElementById("statusText").textContent = "Backend offline";
  }
}

async function loadDashboard() {
  try {
    const resp = await fetch(`${API}/messages?limit=50`);
    const data = await resp.json();
    if (!data.success) { showTableMsg("Failed to load data."); return; }
    renderStats(data.stats, data.total_on_chain, data.blockchain_connected);
    renderTable(data.messages || []);
  } catch (err) {
    showTableMsg(`Network error: ${err.message}`);
  }
}

function renderStats(s, onChain, bcConnected) {
  if (!s) return;
  document.getElementById("statTotal").textContent    = s.total    ?? 0;
  document.getElementById("statValid").textContent    = s.valid    ?? 0;
  document.getElementById("statInvalid").textContent  = s.invalid  ?? 0;
  document.getElementById("statTampered").textContent = s.tampered ?? 0;
  document.getElementById("statPhishing").textContent = s.phishing ?? 0;
  document.getElementById("statOnChain").textContent  = onChain    ?? "—";
}

function renderTable(messages) {
  const tbody = document.getElementById("messagesBody");
  if (!messages.length) {
    showTableMsg("No messages yet. Send your first secure message!");
    return;
  }
  tbody.innerHTML = messages.map(m => `
    <tr>
      <td>${m.id}</td>
      <td>${escHtml(m.email)}</td>
      <td title="${escHtml(m.message)}"
        style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
        ${escHtml(m.message.slice(0, 50))}${m.message.length > 50 ? "…" : ""}
      </td>
      <td>${dashBadge(m.status, m.is_phishing)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:6px">
          <span>${m.trust_score ?? "—"}</span>
          <div style="width:50px;height:5px;background:var(--border);
                      border-radius:3px;overflow:hidden">
            <div style="height:100%;width:${m.trust_score ?? 0}%;
                        background:${trustColor(m.trust_score)};
                        border-radius:3px"></div>
          </div>
        </div>
      </td>
      <td class="tx-hash" title="${m.tx_hash || ''}">
        ${truncateDash(m.tx_hash, 14)}
      </td>
      <td style="white-space:nowrap;color:var(--text-muted)">
        ${formatDate(m.timestamp)}
      </td>
    </tr>
  `).join("");
}

function showTableMsg(msg) {
  document.getElementById("messagesBody").innerHTML =
    `<tr><td colspan="7"
      style="text-align:center;color:var(--text-muted);padding:32px">
      ${msg}</td></tr>`;
}

function dashBadge(status, isPhishing) {
  if (isPhishing) return `<span class="badge badge-phishing">🚫 PHISHING</span>`;
  const map = {
    valid:    ["badge-valid",    "✅"],
    invalid:  ["badge-invalid",  "❌"],
    tampered: ["badge-tampered", "⚠️"],
    pending:  ["badge-pending",  "⏳"],
  };
  const [cls, icon] = map[status] || ["badge-pending", "⏳"];
  return `<span class="badge ${cls}">${icon} ${(status||"").toUpperCase()}</span>`;
}

function trustColor(score) {
  if (!score)      return "var(--text-muted)";
  if (score >= 70) return "var(--accent-green)";
  if (score >= 40) return "var(--accent-yellow)";
  return "var(--accent-red)";
}

function truncateDash(s, n) {
  if (!s) return "—";
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function escHtml(s) {
  return (s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function formatDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined,
      { dateStyle: "short", timeStyle: "short" });
  } catch { return iso; }
}