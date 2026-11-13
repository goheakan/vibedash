"use strict";

const $ = (id) => document.getElementById(id);
const ui = {
  rail: $("rail"),
  tabs: $("tabs"),
  top: $("top"),
  main: $("main"),
  drawer: $("drawer"),
  scrim: $("scrim"),
  palette: $("palette"),
  open: $("open-project"),
  help: $("help"),
  crash: $("crash"),
};

const state = {
  data: null,
  workspace: { active: "", projects: [] },
  workspaceSig: "",
  projectId: "",
  projectError: "",
  remembered: {},
  view: "now",
  filter: "pending",
  selected: null,
  theme: localStorage.getItem("pd-theme") || "dark",
  seq: "",
  paletteOn: false,
  paletteQ: "",
  paletteI: 0,
};

document.documentElement.dataset.theme = state.theme;

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function safeUrl(href) {
  const t = String(href || "").trim();
  if (/^https?:\/\//i.test(t) || /^\.?\.?\/[\w./-]+$/.test(t) || /^[\w./-]+\.md$/i.test(t)) {
    return t;
  }
  return "";
}

function inlineMd(text) {
  let s = esc(text);
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, href) => {
    const u = safeUrl(href);
    return u ? `<a href="${esc(u)}" rel="noreferrer">${label}</a>` : label;
  });
  return s;
}

function renderMd(src) {
  const lines = String(src || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith("```")) {
      const buf = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) {
        buf.push(lines[i]);
        i += 1;
      }
      html.push(`<pre><code>${esc(buf.join("\n"))}</code></pre>`);
      i += 1;
      continue;
    }
    if (/^\|/.test(line) && i + 1 < lines.length && /^\|[\s:|-]+\|/.test(lines[i + 1])) {
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) {
        rows.push(lines[i]);
        i += 1;
      }
      const cells = (row) => row.split("|").slice(1, -1).map((c) => c.trim());
      const head = cells(rows[0]);
      const body = rows.slice(2).map(cells);
      html.push("<table><thead><tr>" + head.map((c) => `<th>${inlineMd(c)}</th>`).join("") + "</tr></thead><tbody>");
      body.forEach((r) => {
        html.push("<tr>" + r.map((c) => `<td>${inlineMd(c)}</td>`).join("") + "</tr>");
      });
      html.push("</tbody></table>");
      continue;
    }
    if (/^### /.test(line)) { html.push(`<h3>${inlineMd(line.slice(4))}</h3>`); i += 1; continue; }
    if (/^## /.test(line)) { html.push(`<h2>${inlineMd(line.slice(3))}</h2>`); i += 1; continue; }
    if (/^# /.test(line)) { html.push(`<h2>${inlineMd(line.slice(2))}</h2>`); i += 1; continue; }
    if (/^[-*] /.test(line)) {
      html.push("<ul>");
      while (i < lines.length && /^[-*] /.test(lines[i])) {
        html.push(`<li>${inlineMd(lines[i].slice(2))}</li>`);
        i += 1;
      }
      html.push("</ul>");
      continue;
    }
    if (/^\d+\. /.test(line)) {
      const start = parseInt(line, 10) || 1;
      html.push(`<ol start="${start}">`);
      while (i < lines.length && /^\d+\. /.test(lines[i])) {
        html.push(`<li>${inlineMd(lines[i].replace(/^\d+\.\s+/, ""))}</li>`);
        i += 1;
      }
      html.push("</ol>");
      continue;
    }
    if (!line.trim()) { i += 1; continue; }
    const buf = [];
    while (i < lines.length && lines[i].trim() && !/^#{1,3} |^[-*] |^\d+\. |^\||^```/.test(lines[i])) {
      buf.push(lines[i]);
      i += 1;
    }
    html.push(`<p>${inlineMd(buf.join(" "))}</p>`);
  }
  return html.join("");
}

function pill(bucket, label) {
  return `<span class="pill ${esc(bucket)}">${esc(label || bucket)}</span>`;
}

function allItems() {
  const d = state.data;
  if (!d) return [];
  return [...d.decisions, ...d.milestones, ...d.sales.filter((s) => !d.decisions.some((x) => x.id === s.id))];
}

function findItem(id) {
  return allItems().find((x) => x.id === id);
}

function openItem(id) {
  const item = findItem(id);
  if (!item) return;
  state.selected = id;
  const el = ui.drawer;
  el.hidden = false;
  ui.scrim.hidden = false;
  el.innerHTML = `
    <header>
      <div>
        ${pill(item.bucket, item.status)}
        <h2>${esc(item.id)} — ${esc(item.title)}</h2>
      </div>
      <button class="ghost" type="button" data-act="close">Fermer</button>
    </header>
    <p class="file">${esc(item.file || "pas encore de fichier")}${item.date ? " · " + esc(item.date) : ""}</p>
    <p>${esc(item.summary)}</p>
    <div class="md">${renderMd(item.body)}</div>`;
  paintListSelection();
}

function closeOverlays() {
  ui.drawer.hidden = true;
  ui.scrim.hidden = true;
  ui.palette.hidden = true;
  ui.open.hidden = true;
  ui.help.hidden = true;
  state.paletteOn = false;
  state.selected = null;
}

function setView(view) {
  if (!state.data) return;
  state.view = view;
  if (state.projectId) state.remembered[state.projectId] = view;
  if (view === "decisions" && state.filter === "all") {
    /* keep */
  } else if (view === "now") {
    state.filter = "pending";
  }
  render();
}

function setTheme(theme) {
  state.theme = theme;
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("pd-theme", theme);
}

function pct(done, total) {
  if (!total) return 0;
  return Math.round((done / total) * 100);
}

function workspaceSig(workspace) {
  return (workspace.projects || [])
    .map((p) => [p.id, p.name, p.pending, p.error || ""].join(":"))
    .join("|");
}

function renderTabs() {
  const projects = state.workspace.projects || [];
  const tabs = projects.map((p) => {
    const active = p.id === state.projectId ? " active" : "";
    const broken = p.error ? " broken" : "";
    const mark = p.pending ? `<span class="count">${esc(p.pending)}</span>` : "";
    const current = p.id === state.projectId ? ' aria-current="page"' : "";
    return `<span class="tab${active}${broken}">
      <button class="tab-name" type="button" data-project="${esc(p.id)}"${current}>${esc(p.name)}${mark}</button>
      <button class="tab-x" type="button" data-close="${esc(p.id)}" aria-label="Retirer ${esc(p.name)} du tableau" title="Retirer du tableau. Les fichiers restent.">×</button>
    </span>`;
  }).join("");
  ui.tabs.innerHTML = `${tabs}<button class="tab-add" type="button" data-act="open">Ouvrir</button>`;
}

function renderIdle(title, tagline, mainHtml) {
  document.title = "VibeDash";
  renderTabs();
  ui.rail.innerHTML = `
    <div class="brand">
      <img src="/static/icon.svg" alt="">
      <div>
        <strong>${esc(title)}</strong>
        <span>local</span>
      </div>
    </div>
    <p class="rail-foot">
      127.0.0.1 seulement<br>
      Markdown = source<br>
      <code>o</code> ouvrir un projet · <code>?</code> aide
    </p>`;
  ui.top.innerHTML = `<div><h1>${esc(title)}</h1><p>${esc(tagline)}</p></div>`;
  ui.main.innerHTML = mainHtml;
}

function renderEmpty() {
  renderIdle(
    "Projets",
    "Un seul tableau, un onglet par projet.",
    `<p class="empty">Aucun projet ouvert. Indique un dossier qui contient déjà un <code>dashboard.toml</code>.</p>
     <p><button class="chip active" type="button" data-act="open">Ouvrir un projet</button></p>`
  );
}

function renderBroken() {
  renderIdle(
    "Projet illisible",
    state.projectError || "lecture impossible",
    `<p class="empty">${esc(state.projectError || "lecture impossible")}. Les autres onglets restent disponibles. Retirer l'onglet ne supprime pas les fichiers.</p>`
  );
}

function showOpen() {
  closeOverlays();
  ui.open.hidden = false;
  ui.scrim.hidden = false;
  ui.open.innerHTML = `
    <div class="open-box">
      <h2>Ouvrir un projet</h2>
      <p class="hint">Dossier qui contient déjà un <code>dashboard.toml</code>. Rien n'est écrit dans ce dossier. Un chemin relatif part du dossier où le serveur a été lancé.</p>
      <input id="open-path" type="text" placeholder="/chemin/vers/le/projet" autocomplete="off" spellcheck="false">
      <p class="form-error" id="open-error" hidden></p>
      <div class="form-actions">
        <button class="ghost" type="button" data-act="close">Annuler</button>
        <button class="chip active" type="button" data-act="open-go">Ouvrir</button>
      </div>
    </div>`;
  const input = $("open-path");
  if (input) input.focus();
}

function submitOpen() {
  const input = $("open-path");
  const err = $("open-error");
  const path = input ? input.value.trim() : "";
  return fetch("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  }).then(async (res) => {
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      if (err) {
        err.hidden = false;
        err.textContent = body.error || "ouverture impossible";
      }
      return;
    }
    state.projectId = body.project.id;
    state.view = state.remembered[state.projectId] || "now";
    state.data = null;
    localStorage.setItem("pd-project", state.projectId);
    closeOverlays();
    await refresh();
  });
}

function selectProject(id) {
  if (!id || (id === state.projectId && state.data)) return Promise.resolve();
  if (state.projectId) state.remembered[state.projectId] = state.view;
  state.projectId = id;
  state.view = state.remembered[id] || "now";
  state.filter = "pending";
  state.selected = null;
  state.data = null;
  localStorage.setItem("pd-project", id);
  closeOverlays();
  return fetch("/api/active", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  }).then(() => refresh());
}

function closeProject(id) {
  return fetch("/api/projects/" + encodeURIComponent(id), { method: "DELETE" }).then(async (res) => {
    if (!res.ok) return;
    if (state.projectId === id) {
      state.projectId = "";
      state.data = null;
    }
    if (localStorage.getItem("pd-project") === id) localStorage.removeItem("pd-project");
    await refresh();
  });
}

function chosenId(workspace) {
  const known = new Set((workspace.projects || []).map((p) => p.id));
  if (state.projectId && known.has(state.projectId)) return state.projectId;
  const stored = localStorage.getItem("pd-project") || "";
  if (stored && known.has(stored)) return stored;
  if (workspace.active && known.has(workspace.active)) return workspace.active;
  return (workspace.projects[0] && workspace.projects[0].id) || "";
}

function renderRail() {
  const d = state.data;
  const s = d.stats;
  const nav = [
    ["now", "Maintenant", "G I", s.pending],
    ["decisions", "Décisions", "G D", `${s.decisions_done}/${s.decisions_total}`],
    ["milestones", "Jalons", "G J", `${s.milestones_done}/${s.milestones_total}`],
    ["sales", d.sales_title || "Vente", "G V", d.sales.length],
  ];
  ui.rail.innerHTML = `
    <div class="brand">
      <img src="/static/icon.svg" alt="">
      <div>
        <strong>${esc(d.project.name)}</strong>
        <span>${esc(d.project.identity || "local")}</span>
      </div>
    </div>
    ${nav.map(([id, label, keys, n]) => `
      <button class="nav-btn ${state.view === id ? "active" : ""}" type="button" data-view="${id}">
        <span>${esc(label)}</span>
        <span>${id === "now" && s.pending ? `<span class="count">${esc(n)}</span>` : `<kbd>${esc(keys)}</kbd>`}</span>
      </button>`).join("")}
    <p class="rail-foot">
      127.0.0.1 seulement<br>
      Markdown = source<br>
      <code>/</code> chercher · <code>?</code> aide
    </p>`;
}

function renderTop() {
  const d = state.data;
  const s = d.stats;
  const current = d.milestones.find((m) => m.bucket === "current");
  ui.top.innerHTML = `
    <div>
      <h1>${esc(d.project.name)}</h1>
      <p>${esc(d.project.tagline)}</p>
    </div>
    <div class="stats">
      <div class="stat"><b>${s.decisions_done}/${s.decisions_total}</b><span>décisions</span>
        <div class="bar" aria-hidden="true"><i style="width:${pct(s.decisions_done, s.decisions_total)}%"></i></div>
      </div>
      <div class="stat"><b>${s.milestones_done}/${s.milestones_total}</b><span>jalons</span>
        <div class="bar" aria-hidden="true"><i style="width:${pct(s.milestones_done, s.milestones_total)}%"></i></div>
      </div>
      <div class="stat"><b>${esc(current ? current.id : "—")}</b><span>en cours</span></div>
    </div>`;
}

function sameLine(a, b) {
  const n = (s) => String(s || "").toLowerCase().replace(/\s+/g, " ").trim();
  return n(a) && n(a) === n(b);
}

function card(item) {
  const extra = item.summary && !sameLine(item.title, item.summary)
    ? `<p>${esc(item.summary)}</p>`
    : "";
  return `
    <button class="card ${esc(item.bucket)}" type="button" data-open="${esc(item.id)}">
      <span class="id">${esc(item.id)}</span>
      <h3>${esc(item.title)}</h3>
      ${extra}
      ${pill(item.bucket, item.status)}
    </button>`;
}

function row(item) {
  return `
    <button class="row ${item.id === state.selected ? "selected" : ""}" type="button" data-open="${esc(item.id)}">
      <span class="id">${esc(item.id)}</span>
      <span class="mid">
        <h3>${esc(item.title)}</h3>
        <p>${esc(item.summary)}</p>
      </span>
      ${pill(item.bucket, item.status)}
    </button>`;
}

function paintListSelection() {
  ui.main.querySelectorAll(".row").forEach((el) => {
    el.classList.toggle("selected", el.getAttribute("data-open") === state.selected);
  });
}

function renderNow() {
  const d = state.data;
  const constraints = d.constraints.map((c) => `<span class="constraint">${esc(c)}</span>`).join("");
  const pending = d.decisions.filter((x) => x.bucket === "pending" || x.bucket === "orientation");
  const current = d.milestones.find((m) => m.bucket === "current");
  return `
    <p class="hint">Ce qui demande une décision ou un feu vert. <kbd>J</kbd>/<kbd>K</kbd> parcourt, <kbd>Entrée</kbd> ouvre.</p>
    ${constraints ? `<div class="constraints">${constraints}</div>` : ""}
    <h2 class="hint" style="text-transform:uppercase;letter-spacing:.08em;color:var(--faint)">À trancher</h2>
    ${pending.length ? `<div class="grid">${pending.map(card).join("")}</div>` : `<p class="empty">Rien en attente. Les décisions sont tranchées.</p>`}
    ${current ? `<h2 class="hint" style="margin-top:22px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint)">Jalon en cours</h2><div class="grid">${card(current)}</div>` : ""}`;
}

function renderDecisions() {
  const chips = [
    ["pending", "À trancher"],
    ["all", "Toutes"],
    ["done", "Tranchées"],
    ["orientation", "Orientation"],
  ];
  let items = state.data.decisions;
  if (state.filter === "pending") items = items.filter((x) => x.bucket === "pending" || x.bucket === "orientation");
  else if (state.filter !== "all") items = items.filter((x) => x.bucket === state.filter);
  return `
    <div class="chips">
      ${chips.map(([id, label]) => `<button class="chip ${state.filter === id ? "active" : ""}" type="button" data-filter="${id}">${esc(label)}</button>`).join("")}
    </div>
    <div class="list">${items.map(row).join("") || `<p class="empty">Aucun élément dans ce filtre.</p>`}</div>`;
}

function renderMilestones() {
  const groups = {
    done: state.data.milestones.filter((m) => m.bucket === "done"),
    current: state.data.milestones.filter((m) => m.bucket === "current"),
    upcoming: state.data.milestones.filter((m) => m.bucket === "upcoming"),
  };
  const steps = state.data.milestones.map((m) =>
    `<button class="step ${esc(m.bucket)}" type="button" data-open="${esc(m.id)}">${esc(m.id)}</button>`
  ).join("");
  return `
    <p class="hint">Fait · en cours · à venir. Un jalon passe à « fait » dès que son fichier <code>Jn.md</code> existe.</p>
    <div class="track">${steps}</div>
    <div class="board">
      <section class="col"><h2>Fait</h2>${groups.done.map(card).join("") || "<p class='hint'>Aucun</p>"}</section>
      <section class="col"><h2>En cours</h2>${groups.current.map(card).join("") || "<p class='hint'>Aucun</p>"}</section>
      <section class="col"><h2>À venir</h2>${groups.upcoming.map(card).join("") || "<p class='hint'>Aucun</p>"}</section>
    </div>`;
}

function renderSales() {
  const items = state.data.sales;
  return `
    <p class="hint">La Play Console reste chez Google. Ici : décisions commerciales et jalon de publication.</p>
    ${items.length ? `<div class="grid">${items.map(card).join("")}</div>` : `<p class="empty">Aucune carte vente. Ajoute <code>lanes.sales</code> dans dashboard.toml.</p>`}`;
}

function render() {
  if (!state.data) return;
  document.title = `${state.data.project.name} — VibeDash`;
  renderTabs();
  renderRail();
  renderTop();
  const views = { now: renderNow, decisions: renderDecisions, milestones: renderMilestones, sales: renderSales };
  ui.main.innerHTML = (views[state.view] || renderNow)();
}

function paletteItems() {
  const q = state.paletteQ.trim().toLowerCase();
  const pool = [
    { id: "view:now", title: "Maintenant", summary: "À trancher + jalon en cours" },
    { id: "view:decisions", title: "Décisions", summary: "Registre D*" },
    { id: "view:milestones", title: "Jalons", summary: "J0…Jn" },
    { id: "view:sales", title: "Vente", summary: "Play, prix, société" },
    { id: "open", title: "Ouvrir un projet", summary: "Dossier avec dashboard.toml" },
    { id: "theme", title: "Changer de thème", summary: "clair / sombre" },
    ...allItems().map((x) => ({ id: x.id, title: `${x.id} — ${x.title}`, summary: x.summary })),
  ];
  return q ? pool.filter((x) => (x.title + x.summary).toLowerCase().includes(q)) : pool;
}

function paletteListHtml() {
  const items = paletteItems();
  if (state.paletteI >= items.length) state.paletteI = 0;
  return `<ul>${items.slice(0, 20).map((it, i) =>
    `<li><button type="button" class="${i === state.paletteI ? "active" : ""}" data-jump="${esc(it.id)}"><span>${esc(it.title)}</span><span class="hint">${esc(it.summary || "")}</span></button></li>`
  ).join("")}</ul>`;
}

function renderPalette() {
  ui.palette.hidden = false;
  ui.scrim.hidden = false;
  state.paletteOn = true;
  if (!$("pal-q")) {
    ui.palette.innerHTML = `<input id="pal-q" type="search" placeholder="Aller à une décision, un jalon, une vue…" autocomplete="off">${paletteListHtml()}`;
    $("pal-q").focus();
    return;
  }
  const ul = ui.palette.querySelector("ul");
  if (ul) ul.outerHTML = paletteListHtml();
}

function runJump(id) {
  closeOverlays();
  if (id === "open") {
    showOpen();
    return;
  }
  if (id === "theme") {
    setTheme(state.theme === "dark" ? "light" : "dark");
    render();
    return;
  }
  if (id.startsWith("view:")) {
    setView(id.slice(5));
    return;
  }
  const item = findItem(id);
  if (!item) return;
  if (item.lane === "dev") setView("milestones");
  else if (item.lane === "sales" && !state.data.decisions.some((d) => d.id === id)) setView("sales");
  else setView("decisions");
  openItem(id);
}

function visibleIds() {
  return [...ui.main.querySelectorAll("[data-open]")].map((el) => el.getAttribute("data-open"));
}

function moveSel(dir) {
  const ids = visibleIds();
  if (!ids.length) return;
  const i = Math.max(0, ids.indexOf(state.selected));
  const next = ids[(i + dir + ids.length) % ids.length];
  state.selected = next;
  paintListSelection();
  const el = ui.main.querySelector(`[data-open="${CSS.escape(next)}"]`);
  if (el) el.focus();
}

function onClick(ev) {
  const t = ev.target.closest("[data-view],[data-filter],[data-open],[data-act],[data-jump],[data-project],[data-close]");
  if (!t) {
    if (ev.target === ui.scrim) closeOverlays();
    return;
  }
  if (t.dataset.close) { enqueue(() => closeProject(t.dataset.close)); return; }
  if (t.dataset.project) { enqueue(() => selectProject(t.dataset.project)); return; }
  if (t.dataset.view) setView(t.dataset.view);
  else if (t.dataset.filter) { state.filter = t.dataset.filter; render(); }
  else if (t.dataset.open) openItem(t.dataset.open);
  else if (t.dataset.act === "close") closeOverlays();
  else if (t.dataset.act === "open") showOpen();
  else if (t.dataset.act === "open-go") enqueue(() => submitOpen());
  else if (t.dataset.jump) runJump(t.dataset.jump);
}

function showHelp() {
  ui.help.hidden = false;
  ui.scrim.hidden = false;
  ui.help.innerHTML = `
    <div class="help">
      <h2>Clavier</h2>
      <table>
        <tr><td>/</td><td>chercher (palette)</td></tr>
        <tr><td>g i / g d / g j / g v</td><td>Maintenant, Décisions, Jalons, Vente</td></tr>
        <tr><td>j / k</td><td>élément suivant / précédent</td></tr>
        <tr><td>Entrée</td><td>ouvrir</td></tr>
        <tr><td>o</td><td>ouvrir un projet</td></tr>
        <tr><td>t</td><td>thème clair / sombre</td></tr>
        <tr><td>?</td><td>cette aide</td></tr>
        <tr><td>Échap</td><td>fermer</td></tr>
      </table>
    </div>`;
}

function onKey(ev) {
  if (ev.target.id === "open-path") {
    if (ev.key === "Escape") { closeOverlays(); ev.preventDefault(); }
    else if (ev.key === "Enter") { enqueue(() => submitOpen()); ev.preventDefault(); }
    return;
  }
  const inField = ev.target.matches("input, textarea");
  if (state.paletteOn && inField) {
    if (ev.key === "Escape") { closeOverlays(); ev.preventDefault(); }
    else if (ev.key === "ArrowDown") { state.paletteI += 1; renderPalette(); ev.preventDefault(); }
    else if (ev.key === "ArrowUp") { state.paletteI = Math.max(0, state.paletteI - 1); renderPalette(); ev.preventDefault(); }
    else if (ev.key === "Enter") {
      const items = paletteItems();
      if (items[state.paletteI]) runJump(items[state.paletteI].id);
      ev.preventDefault();
    }
    return;
  }
  if (inField) return;
  if (ev.key === "Escape") { closeOverlays(); state.seq = ""; return; }
  if (ev.key === "?" || (ev.shiftKey && ev.key === "/")) { showHelp(); ev.preventDefault(); return; }
  if (ev.key === "/" || ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "k")) {
    state.paletteQ = "";
    state.paletteI = 0;
    renderPalette();
    const pal = $("pal-q");
    if (pal) {
      pal.value = "";
      pal.focus();
    }
    ev.preventDefault();
    return;
  }
  if (ev.key === "o") { state.seq = ""; showOpen(); ev.preventDefault(); return; }
  if (ev.key === "t") { setTheme(state.theme === "dark" ? "light" : "dark"); return; }
  if (ev.key === "j") { moveSel(1); ev.preventDefault(); return; }
  if (ev.key === "k") { moveSel(-1); ev.preventDefault(); return; }
  if (ev.key === "Enter" && state.selected) { openItem(state.selected); ev.preventDefault(); return; }
  if (ev.key === "g") { state.seq = "g"; return; }
  if (state.seq === "g") {
    state.seq = "";
    const map = { i: "now", d: "decisions", j: "milestones", v: "sales" };
    if (map[ev.key]) { setView(map[ev.key]); ev.preventDefault(); }
  }
}

ui.palette.addEventListener("input", (ev) => {
  if (ev.target.id === "pal-q") {
    state.paletteQ = ev.target.value;
    state.paletteI = 0;
    renderPalette();
  }
});

document.addEventListener("click", onClick);
document.addEventListener("keydown", onKey);

async function refresh() {
  const res = await fetch("/api/projects", { cache: "no-store" });
  if (!res.ok) throw new Error("HTTP " + res.status);
  const workspace = await res.json();
  const sig = workspaceSig(workspace);
  const sigChanged = sig !== state.workspaceSig;
  state.workspace = workspace;
  state.workspaceSig = sig;
  const id = chosenId(workspace);
  state.projectId = id;
  if (!id) {
    state.data = null;
    state.projectError = "";
    if (sigChanged || !ui.main.querySelector("[data-act='open']")) renderEmpty();
    ui.crash.hidden = true;
    return;
  }
  const card = (workspace.projects || []).find((p) => p.id === id);
  if (card && card.error) {
    const same = !state.data && state.projectError === card.error;
    state.data = null;
    state.projectError = card.error;
    if (!same || sigChanged) renderBroken();
    ui.crash.hidden = true;
    return;
  }
  const st = await fetch("/api/state?project=" + encodeURIComponent(id), { cache: "no-store" });
  if (!st.ok) {
    const body = await st.json().catch(() => ({}));
    state.data = null;
    state.projectError = body.error || "lecture impossible";
    renderBroken();
    ui.crash.hidden = true;
    return;
  }
  const data = await st.json();
  const changed = !state.data || state.data.rev !== data.rev || state.data.project.id !== data.project.id;
  state.data = data;
  state.projectError = "";
  if (changed) render();
  else if (sigChanged) renderTabs();
  ui.crash.hidden = true;
}

let tail = Promise.resolve();
function enqueue(task) {
  const run = tail.then(task, task);
  tail = run.then(() => undefined, () => undefined);
  return run;
}

enqueue(() => refresh().catch((err) => {
  ui.crash.hidden = false;
  ui.crash.textContent = "Impossible de lire le tableau : " + err.message;
}));
setInterval(() => {
  enqueue(() => refresh().catch((err) => {
    ui.crash.hidden = false;
    ui.crash.textContent = "Impossible de lire le tableau : " + err.message;
  }));
}, 2500);
