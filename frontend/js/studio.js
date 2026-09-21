const params = new URLSearchParams(location.search);
const discId = params.get("id");

const $ = id => document.getElementById(id);
const transcriptEl = $("transcript");
const guestListEl = $("guestList");
const consensusEl = $("consensus");
const divergenceEl = $("divergence");

let guestsById = {};
let started = false;

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderGuests(guests) {
  guestsById = {};
  guestListEl.innerHTML = guests.map(g => {
    guestsById[g.id] = g;
    const roleTag = g.role === "host" ? "主持" : "专家";
    return `
      <div class="guest-card" id="guest-${g.id}" style="border-left-color:${g.color}">
        <div class="row1">
          <span class="chip" style="background:${g.color}"></span>
          <span class="name">${escapeHtml(g.name)}</span>
          <span class="status-pill idle" id="pill-${g.id}">待机</span>
        </div>
        <div class="row2"><span class="role-tag">${roleTag}</span> ${escapeHtml(g.title)}</div>
        <div class="row2" id="thought-${g.id}" style="color:var(--amber);"></div>
      </div>`;
  }).join("");
  $("guestCount").textContent = `${guests.length} 人`;
}

function appendMessage(m) {
  const roleTag = guestsById[m.guest_id]?.role === "host" ? "主持" : "专家";
  const div = document.createElement("div");
  div.className = "msg" + (guestsById[m.guest_id]?.role === "host" ? " host" : "");
  div.innerHTML = `
    <div class="who">
      <span class="chip" style="background:${m.color}"></span>
      <strong>${escapeHtml(m.name)}</strong>
      <span class="role-tag">${roleTag}</span>
      <span style="color:var(--muted)">· ${escapeHtml(m.title)}</span>
    </div>
    <div class="bubble" style="border-left-color:${m.color}">${escapeHtml(m.content)}</div>`;
  transcriptEl.appendChild(div);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
  $("msgCount").textContent = `${transcriptEl.children.length} 条`;
}

function renderConsensus(list, box) {
  box.innerHTML = list.length
    ? list.map(c => `<div class="cd-item c">✓ ${escapeHtml(c)}</div>`).join("")
    : '<div class="cd-empty">讨论进行中…</div>';
}
function renderDivergence(list, box) {
  box.innerHTML = list.length
    ? list.map(d => `<div class="cd-item d">◆ ${escapeHtml(d)}</div>`).join("")
    : '<div class="cd-empty">暂无明显分歧</div>';
}

function renderStatuses(statuses) {
  for (const [gid, st] of Object.entries(statuses)) {
    const pill = $(`pill-${gid}`);
    const thought = $(`thought-${gid}`);
    const card = $(`guest-${gid}`);
    if (!pill) continue;
    pill.className = "status-pill " + st.status;
    pill.textContent = st.status === "speaking" ? "发言中" : st.status === "preparing" ? "准备" : "待机";
    if (thought) thought.textContent = (st.thought && (st.status === "speaking" || st.status === "preparing")) ? "💬 " + st.thought : "";
    if (card) card.classList.toggle("speaking", st.status === "speaking");
  }
}

function setLive(on, text) {
  $("liveDot").classList.toggle("off", !on);
  $("statusText").textContent = text || "";
}

function addSummaryBanner(text) {
  const existing = document.querySelector(".summary-banner");
  if (existing) existing.remove();
  const banner = document.createElement("div");
  banner.className = "summary-banner";
  banner.innerHTML = `<strong style="color:var(--gold)">主持人总结</strong><br/>${escapeHtml(text)}`;
  transcriptEl.appendChild(banner);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

async function ensureStarted(disc) {
  if (disc.status === "pending" && !started) {
    started = true;
    await fetch(`/api/discussions/${discId}/start`, { method: "POST" });
  }
}

async function init() {
  try {
    const disc = await fetch(`/api/discussions/${discId}`).then(r => r.json());
    $("topicTitle").textContent = "《" + disc.topic + "》";
    renderGuests(disc.guests);
    disc.messages.forEach(appendMessage);
    renderConsensus(disc.consensus, consensusEl);
    renderDivergence(disc.divergence, divergenceEl);
    if (disc.summary) addSummaryBanner(disc.summary);
    setLive(disc.status === "active",
      disc.status === "ended" ? "已结束" : disc.status === "active" ? "直播中" : "待开始");

    await ensureStarted(disc);
  } catch (e) {
    transcriptEl.innerHTML = `<div class="cd-empty">加载失败：${escapeHtml(e.message)}</div>`;
    return;
  }

  const es = new EventSource(`/api/discussions/${discId}/events`);
  es.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    switch (data.type) {
      case "history":
        // Already rendered from REST; ignore (kept for robustness).
        break;
      case "message": appendMessage(data.message); break;
      case "consensus":
        renderConsensus(data.consensus, consensusEl);
        renderDivergence(data.divergence, divergenceEl);
        break;
      case "agent_status": renderStatuses(data.statuses); break;
      case "summary": addSummaryBanner(data.summary); break;
      case "status":
        setLive(data.status === "active",
          data.status === "ended" ? "已结束" : "直播中");
        break;
      case "error":
        transcriptEl.innerHTML += `<div class="cd-empty">⚠ ${escapeHtml(data.message)}</div>`;
        break;
    }
  };
  es.onerror = () => { /* browser auto-reconnects */ };
}

init();
