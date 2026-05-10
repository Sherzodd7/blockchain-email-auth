// frontend/js/verify.js — исправленная версия для SPA

async function checkStatusVerify() {
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

// ── Verify ────────────────────────────────────────────────────────────────
async function verifyMessage() {
  // используем правильные id из нового index.html
  const message   = document.getElementById("verifyMessage").value.trim();
  const signature = document.getElementById("verifySignature").value.trim();
  const btn       = document.getElementById("verifyBtn");
  const spinner   = document.getElementById("verifySpinner");

  document.getElementById("verifyError").classList.remove("show");
  document.getElementById("verdictPanel").classList.remove("show");

  if (!message)   return showVerifyError("Введи оригинальное сообщение.");
  if (!signature) return showVerifyError("Вставь base64 подпись.");

  btn.disabled = true;
  spinner.classList.add("show");

  try {
    const resp = await fetch(`${API}/verify`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message, signature }),
    });
    const data = await resp.json();

    if (!resp.ok || !data.success) {
      showVerifyError(data.error || "Server error.");
      return;
    }
    renderVerdict(data);

  } catch (err) {
    showVerifyError(`Network error: ${err.message}`);
  } finally {
    btn.disabled = false;
    spinner.classList.remove("show");
  }
}

// ── Render Verdict ────────────────────────────────────────────────────────
const VERDICT_MAP = {
  VALID:     { icon: "✅", color: "var(--accent-green)",  label: "VALID"     },
  INVALID:   { icon: "❌", color: "var(--accent-red)",    label: "INVALID"   },
  TAMPERED:  { icon: "⚠️", color: "var(--accent-yellow)", label: "TAMPERED"  },
  NOT_FOUND: { icon: "❔", color: "var(--text-muted)",    label: "NOT FOUND" },
};

function renderVerdict(data) {
  const panel = document.getElementById("verdictPanel");
  panel.classList.add("show");

  const v = VERDICT_MAP[data.result] || VERDICT_MAP.NOT_FOUND;

  document.getElementById("verdictIcon").textContent = v.icon;
  const vt = document.getElementById("verdictText");
  vt.textContent = v.label;
  vt.style.color = v.color;
  document.getElementById("verdictDetail").textContent = data.details || "";

  const sigEl = document.getElementById("detSig");
  sigEl.innerHTML = data.sig_valid
    ? '<span style="color:var(--accent-green)">✔ Valid</span>'
    : '<span style="color:var(--accent-red)">✘ Invalid</span>';

  const chainEl = document.getElementById("detChain");
  chainEl.innerHTML = data.hash_on_chain
    ? '<span style="color:var(--accent-green)">✔ Found on-chain</span>'
    : '<span style="color:var(--accent-red)">✘ Not found</span>';

  document.getElementById("detHash").textContent = data.hash || "—";

  const ts = data.blockchain_info?.timestamp;
  if (ts && ts > 0) {
    document.getElementById("detTxRow").style.display = "flex";
    document.getElementById("detTs").textContent =
      new Date(ts * 1000).toLocaleString();
  }
}

function showVerifyError(msg) {
  const el = document.getElementById("verifyError");
  document.getElementById("verifyErrorText").textContent = msg;
  el.classList.add("show");
}