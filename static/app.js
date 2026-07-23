/* app.js — 지도 렌더링 + 폴링 로직.
   DOM 요소를 매번 새로 그리지 않고 위치(left/top)만 갱신해서
   CSS transition으로 NPC가 실제로 "움직이는" 것처럼 보이게 한다. */

const ZONE_META = {
  "카페": { icon: "☕", cls: "cafe" },
  "도서관": { icon: "📚", cls: "library" },
  "광장": { icon: "🏛️", cls: "plaza" },
  "공원": { icon: "🌳", cls: "park" },
};

const NPC_EMOJI = ["🐱", "🦊", "🐻", "🐰", "🐼", "🦉"];
const TAG_LABEL = { event: "이벤트", dialogue: "대사", action: "행동", meet: "만남", move: "이동" };

let autoPlay = false;
let busy = false;
let markerEls = {};

function hashOf(name) {
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 997;
  return h;
}

function pickEmoji(name) {
  return NPC_EMOJI[hashOf(name) % NPC_EMOJI.length];
}

async function fetchState() {
  const res = await fetch("/api/state");
  return res.json();
}

async function postTick() {
  const res = await fetch("/api/tick", { method: "POST" });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "알 수 없는 오류가 발생했습니다.");
  return data;
}

async function postReset() {
  const res = await fetch("/api/reset", { method: "POST" });
  return res.json();
}

function renderZones(locations) {
  const map = document.getElementById("map");
  if (map.dataset.zonesRendered) return;
  for (const [name, pos] of Object.entries(locations)) {
    const meta = ZONE_META[name] || { icon: "📍", cls: "" };
    const el = document.createElement("div");
    el.className = `zone ${meta.cls}`;
    el.style.left = pos.x + "%";
    el.style.top = pos.y + "%";
    el.innerHTML = `<div class="icon">${meta.icon}</div><div class="name">${name}</div>`;
    map.appendChild(el);
  }
  map.dataset.zonesRendered = "1";
}

function renderNpcs(state) {
  const map = document.getElementById("map");
  const locations = state.locations;
  const groups = {};
  for (const npc of state.npcs) {
    (groups[npc.location] = groups[npc.location] || []).push(npc);
  }

  for (const [loc, npcs] of Object.entries(groups)) {
    const base = locations[loc];
    if (!base) continue;
    const n = npcs.length;
    npcs.forEach((npc, i) => {
      const angle = ((360 / Math.max(n, 1)) * i * Math.PI) / 180;
      const radius = n > 1 ? 9 : 0;
      const x = base.x + Math.cos(angle) * radius;
      const y = base.y + Math.sin(angle) * radius;

      let el = markerEls[npc.name];
      if (!el) {
        el = document.createElement("div");
        el.className = "npc-marker";
        el.id = "npc-" + npc.name;
        el.innerHTML = `
          <div class="npc-bubble" id="bubble-${npc.name}"></div>
          <div class="npc-avatar">${pickEmoji(npc.name)}</div>
          <div class="npc-name">${npc.name}</div>
        `;
        map.appendChild(el);
        markerEls[npc.name] = el;
      }
      el.style.left = x + "%";
      el.style.top = y + "%";
    });
  }
}

function showBubble(name, text) {
  const bubble = document.getElementById("bubble-" + name);
  if (!bubble) return;
  bubble.textContent = text;
  bubble.classList.add("show");
  clearTimeout(bubble._timer);
  bubble._timer = setTimeout(() => bubble.classList.remove("show"), 4000);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderLog(log) {
  const panel = document.getElementById("log-entries");
  panel.innerHTML = log
    .map((e) => {
      const who = e.npc ? `<b>${escapeHtml(e.npc)}</b> ` : "";
      return `<div class="log-entry"><span class="tag ${e.type}">${TAG_LABEL[e.type] || e.type}</span>${who}${escapeHtml(e.text)}</div>`;
    })
    .join("");
  panel.scrollTop = panel.scrollHeight;
}

function render(state) {
  document.getElementById("clock").textContent = `⏱ ${state.time} (tick ${state.tick})`;
  renderZones(state.locations);
  renderNpcs(state);
  renderLog(state.log);

  state.log
    .filter((e) => e.type === "dialogue" && e.tick === state.tick)
    .forEach((e) => showBubble(e.npc, e.text));
}

function setBusy(v) {
  busy = v;
  document.getElementById("tick-btn").disabled = v;
  document.getElementById("status").textContent = v
    ? "AI가 생각 중..."
    : autoPlay
    ? "자동 재생 중"
    : "대기 중";
}

function showError(msg) {
  const box = document.getElementById("error-box");
  box.textContent = msg;
  box.classList.add("show");
}
function hideError() {
  document.getElementById("error-box").classList.remove("show");
}

async function doTick() {
  if (busy) return;
  setBusy(true);
  hideError();
  try {
    const state = await postTick();
    render(state);
  } catch (e) {
    showError(e.message);
    autoPlay = false;
    document.getElementById("auto-btn").classList.remove("toggled");
  } finally {
    setBusy(false);
    if (autoPlay) setTimeout(doTick, 1500);
  }
}

document.getElementById("tick-btn").addEventListener("click", doTick);

document.getElementById("auto-btn").addEventListener("click", () => {
  autoPlay = !autoPlay;
  document.getElementById("auto-btn").classList.toggle("toggled", autoPlay);
  document.getElementById("status").textContent = autoPlay ? "자동 재생 중" : "대기 중";
  if (autoPlay && !busy) doTick();
});

document.getElementById("reset-btn").addEventListener("click", async () => {
  autoPlay = false;
  document.getElementById("auto-btn").classList.remove("toggled");
  hideError();
  markerEls = {};
  const map = document.getElementById("map");
  map.innerHTML = "";
  map.dataset.zonesRendered = "";
  const state = await postReset();
  render(state);
});

(async function init() {
  const state = await fetchState();
  render(state);
})();
