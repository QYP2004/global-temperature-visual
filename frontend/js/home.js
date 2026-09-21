async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t || r.statusText);
  }
  return r.json();
}

const listEl = document.getElementById("list");
const statusMap = { pending: "待确认阵容", active: "进行中", ended: "已结束" };

async function refreshList() {
  try {
    const items = await api("/api/discussions");
    if (!items.length) {
      listEl.innerHTML = '<div class="empty">还没有讨论，发起一场吧。</div>';
      return;
    }
    listEl.innerHTML = items.map(d => `
      <div class="disc-item">
        <div class="disc-meta">
          <div class="t">${escapeHtml(d.topic)}</div>
          <div class="s">${d.expert_count} 位专家 · ${d.message_count} 条发言 ·
            <span class="badge ${d.status}">${statusMap[d.status] || d.status}</span></div>
        </div>
        <div style="display:flex;gap:8px;">
          ${d.status === "pending"
            ? `<button class="btn-primary" data-confirm="${d.id}">确认开始</button>`
            : `<button class="btn-ghost" data-watch="${d.id}">进入观察</button>`}
        </div>
      </div>`).join("");
  } catch (e) {
    listEl.innerHTML = `<div class="empty">加载失败：${escapeHtml(e.message)}</div>`;
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

document.getElementById("createBtn").addEventListener("click", async () => {
  const topic = document.getElementById("topic").value.trim();
  const count = parseInt(document.getElementById("count").value, 10);
  const hint = document.getElementById("createHint");
  const btn = document.getElementById("createBtn");
  if (!topic) { hint.textContent = "请先输入话题。"; return; }
  btn.disabled = true;
  hint.textContent = "正在生成嘉宾阵容…";
  try {
    const d = await api("/api/discussions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, expert_count: count }),
    });
    location.href = `/studio?id=${d.id}`;
  } catch (e) {
    hint.textContent = "失败：" + e.message;
    btn.disabled = false;
  }
});

listEl.addEventListener("click", async (e) => {
  const watch = e.target.getAttribute("data-watch");
  const confirm = e.target.getAttribute("data-confirm");
  if (watch) location.href = `/studio?id=${watch}`;
  if (confirm) {
    await api(`/api/discussions/${confirm}/start`, { method: "POST" });
    location.href = `/studio?id=${confirm}`;
  }
});

refreshList();
setInterval(refreshList, 5000);
