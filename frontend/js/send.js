

// ── Check blockchain / backend status on load ─────────────────────────────
async function checkStatus() {
  try {
    const r = await fetch(`${API}/health`);
    const d = await r.json();
    const dot  = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    if (d.blockchain.includes("connected")) {
      dot.className = "status-dot online";
      text.textContent = "Blockchain online";
    } else {
      dot.className = "status-dot";
      text.textContent = "Mock mode (Ganache offline)";
    }
  } catch {
    document.getElementById("statusDot").className = "status-dot offline";
    document.getElementById("statusText").textContent = "Backend offline";
  }
}

// ── Send Message ──────────────────────────────────────────────────────────
async function sendMessage() {
  const email   = document.getElementById("email").value.trim();
  const message = document.getElementById("message").value.trim();
  const btn     = document.getElementById("sendBtn");
  const spinner = document.getElementById("sendSpinner");

  // Clear previous UI state
  hideAlert("sendError");
  hideAlert("phishingAlert");
  document.getElementById("resultPanel").classList.remove("show");

  // Basic client-side validation
  if (!email) return showAlert("sendError", "Please enter a sender email address.");
  if (!message) return showAlert("sendError", "Please enter a message body.");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
    return showAlert("sendError", "Invalid email format.");

  // Loading state
  btn.disabled = true;
  spinner.classList.add("show");

  try {
    const resp = await fetch(`${API}/send`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ email, message }),
    });
    const data = await resp.json();

    if (!resp.ok || !data.success) {
      showAlert("sendError", data.error || "Server error. Please try again.");
      return;
    }

    renderResult(data);

  } catch (err) {
    showAlert("sendError", `Network error: ${err.message}`);
  } finally {
    btn.disabled = false;
    spinner.classList.remove("show");
  }
}

// ── Render send result ────────────────────────────────────────────────────
function renderResult(data) {
  const panel = document.getElementById("resultPanel");
  panel.classList.add("show");

  // Status badge
  document.getElementById("resStatus").innerHTML = badgeHtml(data.status);

  // Trust score
  const trust = data.trust_score ?? 0;
  document.getElementById("resTrust").textContent = `${trust} / 100`;
  const bar = document.getElementById("trustBar");
  bar.style.width = `${trust}%`;
  bar.className   = "trust-bar-fill " +
    (trust >= 70 ? "high" : trust >= 40 ? "medium" : "low");

  // Crypto / blockchain fields
  setText("resHash", data.hash      || "—");
  setText("resTx",   data.tx_hash   || "—");
  setText("resBC",   data.blockchain_status);
  setText("resSig",  data.signature || "—");


  // Phishing warning
  const sec = data.security || {};
  const banner = document.getElementById("phishingBanner");
  if (sec.is_phishing) {
    banner.classList.add("show");
    document.getElementById("phishingFlags").textContent =
      (sec.flags || []).join(" • ") || "Suspicious content detected.";

    showAlert("phishingAlert",
      `⚠️ Phishing risk (${(sec.confidence * 100).toFixed(0)}% confidence) — ${sec.risk_level} risk.`);
  } else {
    banner.classList.remove("show");
  }
}

// ── UI helpers ────────────────────────────────────────────────────────────
function showAlert(id, msg) {
  const el = document.getElementById(id);
  el.querySelector("span:last-child").textContent = msg;
  el.classList.add("show");
}
function hideAlert(id) { document.getElementById(id).classList.remove("show"); }
function setText(id, val) { document.getElementById(id).textContent = val ?? "—"; }
function truncate(s, n) { return s && s.length > n ? s.slice(0, n) + "…" : (s || "—"); }

function badgeHtml(status) {
  const map = {
    valid:    "badge-valid ✅",
    invalid:  "badge-invalid ❌",
    tampered: "badge-tampered ⚠️",
    phishing: "badge-phishing 🚫",
    pending:  "badge-pending ⏳",
  };
  const cls = map[status] ? map[status].split(" ")[0] : "badge-pending";
  const icon = map[status] ? map[status].split(" ")[1] : "?";
  return `<span class="badge ${cls}">${icon} ${status?.toUpperCase()}</span>`;
}


