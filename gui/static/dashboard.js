const REFRESH_INTERVAL_MS = 2000;
const ONLINE_THRESHOLD_SECONDS = 30;
const HISTORY_POINTS = 30;

const API_URL = "/api/vms";
const stressUrl = (name) => `/api/vms/${encodeURIComponent(name)}/stress`;

const ICON_REFRESH = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/></svg>`;
const ICON_THEME = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor"/></svg>`;

document.body.innerHTML = `
  <main class="shell">
    <header class="topbar">
      <div class="title-group">
        <h1>Group 17</h1>
        <span class="subtitle">VM monitor</span>
        <div class="chips" id="chips"></div>
      </div>
      <div class="topbar-tools">
        <span class="status-pill" id="status-btn" role="status" title="Connecting">
          <span class="live-dot wait" id="live-dot"></span>
          <span id="status-text">Connecting</span>
          <span class="status-time" id="status-time"></span>
        </span>
        <button class="icon-btn" id="theme-btn" type="button" aria-label="Switch light or dark theme" title="Switch theme">${ICON_THEME}</button>
        <button class="icon-btn" id="refresh-btn" type="button" aria-label="Refresh now" title="Refresh now">${ICON_REFRESH}</button>
      </div>
    </header>
    <section id="featured" aria-live="polite"></section>
    <section id="vm-grid" class="vm-grid" aria-live="polite"></section>
  </main>`;

const featuredEl = document.querySelector("#featured");
const vmGrid = document.querySelector("#vm-grid");
const statusBtn = document.querySelector("#status-btn");
const statusText = document.querySelector("#status-text");
const statusTime = document.querySelector("#status-time");
const liveDot = document.querySelector("#live-dot");
const refreshBtn = document.querySelector("#refresh-btn");
const themeBtn = document.querySelector("#theme-btn");
const chipsEl = document.querySelector("#chips");

const netHistory = new Map(); // vm name -> { last, rates: [{up, down}] }
let featuredName = null;      // VM shown in the main panel (click a card name to change)
const stressing = new Set();  // vm names with a stress test in flight
let workloadToken = null;

/* ---------- helpers ---------- */
function latestNumber(values) {
  if (typeof values === "number") return values;
  if (!Array.isArray(values) || values.length === 0) return null;
  const value = Number(values[values.length - 1]);
  return Number.isFinite(value) ? value : null;
}
const percent = (v) => (v === null ? "--" : `${v.toFixed(v % 1 === 0 ? 0 : 1)}%`);
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
const heatOf = (v) => (v === null ? "" : v >= 90 ? "heat-hot" : v >= 75 ? "heat-warm" : "");

function bytes(value) {
  if (!Number.isFinite(Number(value))) return "--";
  let amount = Number(value);
  const units = ["B", "K", "M", "G", "T"];
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) { amount /= 1024; unit += 1; }
  return `${amount.toFixed(unit === 0 || amount >= 100 ? 0 : 1)}${units[unit]}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

function isOnline(vm) {
  return Date.now() / 1000 - Number(vm.updated_at) <= ONLINE_THRESHOLD_SECONDS;
}

function ago(vm) {
  const s = Math.max(0, Date.now() / 1000 - Number(vm.updated_at));
  if (!Number.isFinite(s)) return "never";
  if (s < 5) return "just now";
  if (s < 60) return `${Math.round(s)}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}
const seenText = (vm, online) => (online ? `Updated ${ago(vm)}` : `Offline, last seen ${ago(vm)}`);

/* ---------- network rate tracking ---------- */
function trackNetwork(vm) {
  const net = (vm.metrics || {})["network-metric"] || {};
  const sent = Number(net.bytes_sent), recv = Number(net.bytes_recv);
  const t = Number(vm.updated_at);
  if (![sent, recv, t].every(Number.isFinite)) return;

  const entry = netHistory.get(vm.name) || { last: null, rates: [] };
  const last = entry.last;
  if (last && t > last.t) {
    const dt = t - last.t;
    entry.rates.push({
      up: Math.max(0, (sent - last.sent) / dt),
      down: Math.max(0, (recv - last.recv) / dt),
    });
    entry.rates = entry.rates.slice(-HISTORY_POINTS);
  }
  if (!last || t > last.t) entry.last = { t, sent, recv };
  netHistory.set(vm.name, entry);
}

/* ---------- chart geometry (viewBox is 100 x 40, stretched to fit) ---------- */
const VB_H = 40;

// Newest sample is always at the right edge; short series grow in from the right.
function coords(series, max) {
  return series.map((v, i) => {
    const x = ((HISTORY_POINTS - series.length + i) / (HISTORY_POINTS - 1)) * 100;
    const y = VB_H - 1.5 - (clamp(v, 0, max) / max) * (VB_H - 4);
    return [x, y];
  });
}
const toPoints = (c) => c.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
const areaPoints = (c) => `${c[0][0].toFixed(2)},${VB_H} ${toPoints(c)} 100,${VB_H}`;
const gridLines = () => [0.25, 0.5, 0.75].map((f) => `<line class="grid" x1="0" x2="100" y1="${VB_H * f}" y2="${VB_H * f}"/>`).join("");

/* ---------- components ---------- */
function barRow(label, rawValue) {
  const value = latestNumber(rawValue);
  const clamped = value === null ? 0 : clamp(value, 0, 100);
  const shown = value === null ? "--" : `${Math.round(value)}%`;
  return `
    <div class="bar-row ${heatOf(value)}">
      <span class="bar-label">${label}</span>
      <div class="meter" role="meter" aria-label="${label} usage" aria-valuenow="${clamped}" aria-valuemin="0" aria-valuemax="100">
        <div class="meter-fill" style="width:${clamped}%"></div>
      </div>
      <span class="bar-value">${shown}</span>
    </div>`;
}

function ring(label, rawValue) {
  const value = latestNumber(rawValue);
  const clamped = value === null ? 0 : clamp(value, 0, 100);
  const r = 36, c = 2 * Math.PI * r;
  const shown = value === null ? "--" : Math.round(value);
  return `
    <div class="gauge ${heatOf(value)}">
      <div class="ring" role="meter" aria-label="${label} usage" aria-valuenow="${clamped}" aria-valuemin="0" aria-valuemax="100">
        <svg viewBox="0 0 88 88" aria-hidden="true">
          <circle class="track" cx="44" cy="44" r="${r}"/>
          <circle class="fill" cx="44" cy="44" r="${r}" transform="rotate(-90 44 44)"
                  stroke-dasharray="${((c * clamped) / 100).toFixed(1)} ${c.toFixed(1)}"/>
        </svg>
        <span class="ring-num">${shown}${value === null ? "" : "<small>%</small>"}</span>
      </div>
      <span>${label}</span>
    </div>`;
}

function networkPanel(vm, { foot = false } = {}) {
  const rates = (netHistory.get(vm.name) || {}).rates || [];
  const now = rates[rates.length - 1];
  const peak = Math.max(1024, ...rates.flatMap((r) => [r.up, r.down]));
  let plot = `<div class="chart-empty">Collecting samples…</div>`;
  if (rates.length > 1) {
    const up = coords(rates.map((r) => r.up), peak);
    const down = coords(rates.map((r) => r.down), peak);
    plot = `
      <svg viewBox="0 0 100 ${VB_H}" preserveAspectRatio="none" role="img" aria-label="Network throughput history">
        ${gridLines()}
        <polygon class="area down" points="${areaPoints(down)}"/>
        <polygon class="area up" points="${areaPoints(up)}"/>
        <polyline class="line down" points="${toPoints(down)}"/>
        <polyline class="line up" points="${toPoints(up)}"/>
      </svg>`;
  }
  return `
    <div class="chart-panel">
      <div class="panel-head">
        <span class="panel-title">Network</span>
        <span class="legend">
          <span><i class="swatch up"></i>Up<b>${now ? bytes(now.up) : "--"}/s</b></span>
          <span><i class="swatch down"></i>Down<b>${now ? bytes(now.down) : "--"}/s</b></span>
        </span>
      </div>
      <div class="plot">${plot}</div>
      ${foot ? `<div class="panel-foot">Chart scale tops out at ${bytes(peak)}/s</div>` : ""}
    </div>`;
}

function cpuPanel(vm) {
  const raw = (vm.metrics || {})["cpu-metric"];
  const series = (Array.isArray(raw) ? raw : []).map(Number).filter(Number.isFinite).slice(-HISTORY_POINTS);
  const value = latestNumber(raw);
  let plot = `<div class="chart-empty">Collecting samples…</div>`;
  if (series.length > 1) {
    const c = coords(series, 100);
    const last = c[c.length - 1];
    plot = `
      <svg viewBox="0 0 100 ${VB_H}" preserveAspectRatio="none" role="img" aria-label="Recent CPU usage">
        ${gridLines()}
        <polygon class="area cpu" points="${areaPoints(c)}"/>
        <polyline class="line cpu" points="${toPoints(c)}"/>
      </svg>
      <span class="marker" style="top:${((last[1] / VB_H) * 100).toFixed(1)}%"></span>`;
  }
  return `
    <div class="chart-panel ${heatOf(value)}">
      <div class="panel-head">
        <span class="panel-title">CPU, last ${HISTORY_POINTS} samples</span>
        <span class="panel-value">${percent(value)}</span>
      </div>
      <div class="plot">${plot}</div>
      <div class="panel-foot">Scale 0 to 100%</div>
    </div>`;
}

function renderFeatured(vm) {
  const m = vm.metrics || {};
  const online = isOnline(vm);
  const hostBadge = m["is_host"] ? `<span"></span>` : "";
  return `
    <article class="hero ${online ? "" : "offline"}">
      <div class="identity">
        <div>
          <h2 class="hero-name"><span class="status-dot ${online ? "" : "offline"}" aria-hidden="true"></span>${escapeHtml(vm.name)}${hostBadge}</h2>
          <p class="seen">${seenText(vm, online)}</p>
        </div>
        <div class="gauges">
          ${ring("Disk", m["disk-metric"])}
          ${ring("Memory", m["memory-metric"])}
          ${ring("Swap", m["swap-metric"])}
        </div>
      </div>
      ${cpuPanel(vm)}
      ${networkPanel(vm, { foot: true })}
    </article>`;
}

function renderCard(vm) {
  const m = vm.metrics || {};
  const online = isOnline(vm);
  const stressStatus = vm.stress || {};
  const busy = stressing.has(vm.name) || ["queued", "running"].includes(stressStatus.status);
  const name = escapeHtml(vm.name);
  const hostBadge = m["is_host"] ? `<span class="host-badge">HOST</span>` : "";
  const stressButton = m["is_host"] ? "" : `
        <button class="stress-btn" type="button" data-stress="${name}" ${busy ? "disabled" : ""}
          title="${escapeHtml(stressStatus.message || "Start workload-simulator.service on this VM")}">
          ${busy ? (stressStatus.status === "queued" ? "Queued…" : "Running…") : "Run workload"}
        </button>`;
  return `
    <article class="card ${online ? "" : "offline"}">
      <header class="card-head">
        <div class="card-title">
          <h3>
            <button class="name-btn" type="button" data-feature="${name}" title="Show ${name} in the main panel">
              <span class="status-dot ${online ? "" : "offline"}" aria-hidden="true"></span>
              <span class="name-text">${name}</span>
              ${hostBadge}
              <span class="go" aria-hidden="true">↑</span>
            </button>
          </h3>
          <span class="seen">${seenText(vm, online)}</span>
        </div>
        ${stressButton}
      </header>
      <div class="card-body">
        <div class="bars">
          ${barRow("CPU", m["cpu-metric"])}
          ${barRow("Disk", m["disk-metric"])}
          ${barRow("Memory", m["memory-metric"])}
          ${barRow("Swap", m["swap-metric"])}
        </div>
        ${networkPanel(vm)}
      </div>
    </article>`;
}

function renderEmptyState() {
  return `
    <div class="empty-state">
      <span class="empty-icon" aria-hidden="true">+</span>
      <strong>No VMs reporting yet</strong>
      <p>Start a slave and point it at this master. It will show up here within a few seconds.</p>
    </div>`;
}

function renderProblem(title, detail) {
  return `
    <div class="empty-state">
      <span class="empty-icon error" aria-hidden="true">!</span>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(detail)}</p>
    </div>`;
}

/* ---------- actions ---------- */
async function runStressTest(name) {
  if (!workloadToken) {
    workloadToken = window.prompt("Enter the shared workload command token:");
  }
  if (!workloadToken) return;

  stressing.add(name);
  refreshDashboard();
  try {
    let response = await requestWorkload(name, workloadToken);
    let result = await response.json();
    if (response.status === 401) {
      workloadToken = window.prompt("Token rejected. Enter the correct workload command token:");
      if (!workloadToken) throw new Error("Workload command token was not provided");
      response = await requestWorkload(name, workloadToken);
      result = await response.json();
    }
    if (!response.ok) {
      if (response.status === 401) workloadToken = null;
      throw new Error(result.error || `Workload request failed (${response.status})`);
    }
    statusBtn.title = `Workload request ${result.status}`;
  } catch (error) {
    statusBtn.title = error.message;
    window.alert(error.message);
  } finally {
    stressing.delete(name);
    refreshDashboard();
  }
}

function requestWorkload(name, token) {
  return fetch(stressUrl(name), {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

document.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-stress]");
  if (btn && !btn.disabled) runStressTest(btn.dataset.stress);
});
document.addEventListener("click", (event) => {
  const el = event.target.closest("[data-feature]");
  if (el) { featuredName = el.dataset.feature; refreshDashboard(); }
});
refreshBtn.addEventListener("click", () => refreshDashboard());

themeBtn.addEventListener("click", () => {
  const root = document.documentElement;
  const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const next = current === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  try { localStorage.setItem("vm-theme", next); } catch (e) { /* storage unavailable */ }
});

/* ---------- data normalising ---------- */
function toSeconds(v) {
  if (v === undefined || v === null || v === "") return NaN;
  let n = Number(v);
  if (!Number.isFinite(n)) n = Date.parse(v) / 1000;   // ISO string
  return n > 1e12 ? n / 1000 : n;                       // milliseconds -> seconds
}

function normalizeVms(data) {
  let list = [];
  const raw = Array.isArray(data) ? data : data && data.vms;
  if (Array.isArray(raw)) list = raw;
  else if (raw && typeof raw === "object") {
    list = Object.entries(raw).map(([name, vm]) => ({ name, ...vm }));
  }
  return list
    .map((vm, i) => ({
      ...vm,
      name: String(vm.name ?? vm.hostname ?? vm.id ?? `VM ${i + 1}`),
      updated_at: toSeconds(vm.updated_at),
      metrics: vm.metrics || {},
    }))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
}

/* ---------- main loop ---------- */
// The page is re-rendered every refresh, so remember which button had keyboard focus.
function focusSelector() {
  const a = document.activeElement;
  if (!a || !a.dataset) return null;
  if (a.dataset.feature !== undefined) return `[data-feature="${CSS.escape(a.dataset.feature)}"]`;
  if (a.dataset.stress !== undefined) return `[data-stress="${CSS.escape(a.dataset.stress)}"]`;
  return null;
}

function setStatus(kind, text, title) {
  liveDot.classList.toggle("down", kind === "down");
  liveDot.classList.toggle("wait", kind === "wait");
  statusText.textContent = text;
  statusBtn.title = title;
}

async function refreshDashboard() {
  try {
    const response = await fetch(API_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`${API_URL} returned ${response.status}`);
    const vms = normalizeVms(await response.json());
    vms.forEach(trackNetwork);
    for (const name of [...netHistory.keys()]) {
      if (!vms.some((vm) => vm.name === name)) netHistory.delete(name);
    }

    const refocus = focusSelector();
    if (!vms.length) {
      featuredEl.innerHTML = "";
      vmGrid.innerHTML = renderEmptyState();
    } else {
      const featured = vms.find((vm) => vm.name === featuredName) || vms[0];
      featuredName = featured.name;
      featuredEl.innerHTML = renderFeatured(featured);
      vmGrid.innerHTML = vms.filter((vm) => vm !== featured).map(renderCard).join("");
    }
    if (refocus) document.querySelector(refocus)?.focus({ preventScroll: true });

    const onlineN = vms.filter(isOnline).length;
    chipsEl.innerHTML = vms.length
      ? `<span class="chip"><b>${vms.length}</b> VM${vms.length === 1 ? "" : "s"}</span><span class="chip"><b>${onlineN}</b> online</span>`
      : "";
    const time = new Date().toLocaleTimeString();
    setStatus("ok", "Live", `Connected, updated ${time}`);
    statusTime.textContent = time;
  } catch (error) {
    setStatus("down", "Disconnected", "API unavailable");
    statusTime.textContent = "";
    if (!vmGrid.querySelector(".card") && !featuredEl.querySelector(".hero")) {
      vmGrid.innerHTML = renderProblem(
        "Can't reach the telemetry API",
        `${error.message}. Check that the master is running and that ${API_URL} is the right route.`
      );
    }
  }
}

refreshDashboard();
setInterval(refreshDashboard, REFRESH_INTERVAL_MS);