/* Midterm Finder — lookup, week ruler, catalogue */
(() => {
"use strict";
const S = window.STUDENTS || {}, CO = window.COURSES || {}, CAT = window.CATALOG || CO, PR = window.PROGRAMMES || {};
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mins = (t) => { const [h, m] = t.split("-")[0].split(":"); return +h * 60 + +m; };
const endMins = (t) => { const [h, m] = t.split("-")[1].split(":"); return +h * 60 + +m; };
const pd = (iso) => new Date(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8));
const wk = (iso, w = "short") => pd(iso).toLocaleDateString("en-GB", { weekday: w });
const dn = (iso) => +iso.slice(8);
const left = (iso) => { const t = new Date(); t.setHours(0, 0, 0, 0); return Math.round((pd(iso) - t) / 864e5); };
const when = (iso) => { const d = left(iso); return d < 0 ? "done" : d === 0 ? "today" : d === 1 ? "tomorrow" : `in ${d} days`; };
const sorted = (l) => l.slice().sort((a, b) => a.d === b.d ? mins(a.t) - mins(b.t) : a.d < b.d ? -1 : 1);
const info = (c) => CAT[c] || CO[c] || { title: c };
const primary = (code) => { for (const [p, c] of Object.entries(CAT)) if (p === code || (c.also || []).includes(code)) return p; return code; };
const exKey = (e) => `${e.c}|${e.d}`;
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const DAYS = [...new Set(Object.values(CAT).map((c) => c.date).filter(Boolean))].sort();
const SLOTS = [...new Set(Object.values(CAT).map((c) => c.time && c.time.split("-")[0]).filter(Boolean))].sort();
const state = { id: "" };

function courseExam(code) {
  const p = primary(code), c = info(p);
  if (!c.date || !c.time) return null;
  return { c: p, sc: p, d: c.date, t: c.time, r: (c.rooms || []).join(", ") || "See schedule", s: "", added: true };
}
const groups = (p) => (p.optionGroups && p.optionGroups.length ? p.optionGroups : [{ id: "options", label: "Programme subjects", options: p.options || [] }]);

function detectProg(id, confirmed) {
  const o = store.get(`mf:prog:${id}`, null);
  if (o && PR[o]) return o;
  if (!id.startsWith("2026")) return null;
  const codes = new Set(confirmed.flatMap((e) => [e.c, e.sc]));
  const n = (k) => (PR[k]?.core || []).filter((c) => codes.has(c)).length;
  if (n("csai") >= 2) return "csai";
  if (n("eng") >= 3) return "eng";
  if (n("csai_upper") >= 2) return "csai_upper";
  return ["csai", "eng", "csai_upper"].find((k) => n(k) >= 1) || null;
}

function schedule(id) {
  const confirmed = sorted(S[id] || []);
  const have = new Set(confirmed.flatMap((e) => [e.c, e.sc]));
  const addedCodes = store.get(`mf:added:${id}`, []).filter((c) => CAT[primary(c)] && !have.has(primary(c)));
  const added = sorted(addedCodes.map(courseExam).filter(Boolean));
  const programme = detectProg(id, confirmed);
  const assumed = [];
  if (programme && PR[programme]) {
    const p = PR[programme], expected = p.expected || 6, slots = store.get(`mf:slots:${id}`, {});
    const codes = new Set([...confirmed, ...added].flatMap((e) => [e.c, e.sc]));
    let n = confirmed.length + added.length;
    for (const code of p.core || []) {
      if (n >= expected) break;
      const ex = CAT[code] && !codes.has(code) && courseExam(code);
      if (ex) { assumed.push({ ...ex, added: false, assumed: true }); codes.add(code); n++; }
    }
    for (const g of groups(p)) {
      if (n >= expected) break;
      if (g.options.some((c) => codes.has(c))) continue;
      let ch = slots[g.id];
      if (!ch || !g.options.includes(ch) || !CAT[ch]) ch = g.default || g.options.find((c) => CAT[c]);
      const ex = ch && !codes.has(ch) && courseExam(ch);
      if (ex) { assumed.push({ ...ex, added: false, assumed: true, slot: g }); codes.add(ch); n++; }
    }
  }
  return { confirmed, added, assumed, all: sorted([...confirmed, ...added, ...assumed]), programme, addedCodes };
}

function clashes(list) {
  const set = new Set();
  for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
    const a = list[i], b = list[j];
    if (a.d === b.d && mins(a.t) < endMins(b.t) && endMins(a.t) > mins(b.t)) { set.add(exKey(a)); set.add(exKey(b)); }
  }
  return set;
}

/* ---------- results ---------- */
function render(id) {
  state.id = id;
  const sc = schedule(id), res = $("#results");
  syncUrl();
  if (!sc.all.length) {
    const first = id.startsWith("2026");
    res.innerHTML = `<div class="res-head"><h2>${esc(id)}</h2></div>
      <div class="note bad"><b>This ID is not on any published seating chart.</b> Check the digits. Some subjects have no chart, so you can still build your timetable from the full exam list.
      ${first ? `<div class="prog"><button data-prog="csai">I’m in Computational Science &amp; AI</button><button data-prog="eng">I’m in Engineering</button></div>` : ""}
      <div class="prog"><button data-open>Add courses by hand</button></div></div>`;
    return;
  }
  const bad = clashes(sc.all);
  const next = sc.all.find((e) => left(e.d) >= 0);
  const nk = next ? exKey(next) : "";
  const cell = (d, s) => sc.all.filter((e) => e.d === d && e.t.startsWith(s));
  let ruler = `<div></div>` + DAYS.map((d) => `<div class="dh">${wk(d)}<b>${dn(d)}</b></div>`).join("");
  let i = 0;
  for (const s of SLOTS) {
    ruler += `<div class="th">${s}</div>`;
    for (const d of DAYS) {
      const hit = cell(d, s);
      if (!hit.length) { ruler += `<div class="c"></div>`; continue; }
      const e = hit[0], cls = [hit.length > 1 || bad.has(exKey(e)) ? "clash" : e.assumed ? "assumed" : exKey(e) === nk ? "next" : ""].join("");
      const [a, b] = (e.sc || e.c).split(" ");
      ruler += `<button class="c ${cls}" style="--i:${i++}" data-go="${esc(exKey(e))}" title="${esc(e.sc || e.c)}, ${esc(e.t)}, ${esc(e.r)}">${esc(a)}<small>${esc(b || "")}</small></button>`;
    }
  }
  const rows = sc.all.map((e, n) => {
    const c = info(e.c), multi = (e.r || "").includes(",");
    const tags = (exKey(e) === nk ? `<span class="tag">next up</span>` : "") + (bad.has(exKey(e)) ? `<span class="tag red">clash</span>` : "") +
      (e.assumed ? `<span class="tag plain">assumed</span>` : e.added ? `<span class="tag plain">added by you</span>` : "") + (e.s ? `<span class="tag plain">section ${esc(e.s)}</span>` : "");
    let acts = "";
    if (e.slot) acts = `<label>Not your ${esc(e.slot.label.toLowerCase())}? <select data-slot="${esc(e.slot.id)}">${e.slot.options.filter((o) => CAT[o]).map((o) => `<option ${o === e.c ? "selected" : ""} value="${esc(o)}">${esc(o)} ${esc(info(o).title)}</option>`).join("")}</select></label>`;
    else if (e.assumed) acts = `<span>From your programme plan. Wrong? Add the right course below.</span>`;
    if (e.added) acts = `<button data-remove="${esc(e.c)}">Remove</button>`;
    return `<li class="ex" style="--n:${n}" id="x-${esc(exKey(e)).replace(/\W/g, "_")}" data-k="${esc(exKey(e))}">
      <div class="d"><b>${dn(e.d)}</b><span>${wk(e.d)}</span></div>
      <div class="info"><h3>${esc(e.sc || e.c)} ${esc(c.title || "")}${tags}</h3><p><b>${esc(e.t.replace("-", " to "))}</b> · ${esc(when(e.d))}</p></div>
      <div class="room${multi ? " multi" : ""}">${esc(e.r)}${multi ? `<small>Room depends on your section</small>` : ""}</div>
      ${acts ? `<div class="acts">${acts}</div>` : ""}</li>`;
  }).join("");
  const parts = [`${sc.confirmed.length} from seating charts`, sc.added.length && `${sc.added.length} added by you`, sc.assumed.length && `${sc.assumed.length} assumed`].filter(Boolean).join(", ");
  res.innerHTML = `<div class="res-head"><h2>${esc(id)}</h2><p><b>${sc.all.length} exams</b> on ${new Set(sc.all.map((e) => e.d)).size} days. ${parts}.${sc.programme ? ` ${esc(PR[sc.programme].label)}.` : ""}</p><button class="share" data-copy>Copy link</button></div>
    ${bad.size ? `<div class="note bad"><b>Two of your exams overlap.</b> Ask your instructors which one to attend.</div>` : ""}
    ${sc.assumed.length ? `<div class="note"><b>${sc.assumed.map((e) => e.c).join(" and ")}</b> ${sc.assumed.length > 1 ? "are" : "is"} assumed from your programme plan because no chart lists you.</div>` : ""}
    <div class="ruler" role="group" aria-label="Your exams by day and time">${ruler}</div>
    <ol class="exams">${rows}</ol>
    <button class="add" data-open>Add a course</button>`;
}

function syncUrl() {
  try { const u = new URL(location.href); if (state.id) u.searchParams.set("id", state.id); else u.searchParams.delete("id"); history.replaceState(null, "", u); } catch {}
}

/* ---------- bubble input ---------- */
const input = $("#idInput"), spans = [...document.querySelectorAll("#bubbles span")];
function paint() {
  const v = input.value;
  $("#clear").hidden = !v;
  spans.forEach((s, i) => { const had = s.textContent; s.textContent = v[i] || ""; s.className = i < v.length ? "f" : i === v.length ? "cur" : ""; if (v[i] && v[i] !== had) { void s.offsetWidth; s.classList.add("pop"); } });
}
function submit() {
  const v = input.value.trim();
  if (v.length === 9) {
    render(v);
    if (matchMedia("(max-width:760px)").matches) { input.blur(); setTimeout(() => $("#results").scrollIntoView({ behavior: "smooth", block: "start" }), 60); }
  }
  else if (!v) { $("#results").innerHTML = ""; state.id = ""; syncUrl(); }
}
input.addEventListener("input", () => { input.value = input.value.replace(/\D/g, "").slice(0, 9); paint(); if (input.value.length === 9) submit(); });
input.addEventListener("focus", paint);
$("#form").addEventListener("submit", (e) => { e.preventDefault(); submit(); });
function setId(v) { input.value = v; paint(); submit(); }

/* ---------- picker ---------- */
const picker = $("#picker");
function drawPicker() {
  const q = $("#pSearch").value.toLowerCase().trim();
  const mine = new Set(store.get(`mf:added:${state.id}`, []));
  const items = Object.entries(CAT).filter(([c, v]) => !q || (c + " " + v.title).toLowerCase().includes(q)).sort((a, b) => a[0].localeCompare(b[0])).slice(0, 80);
  $("#pList").innerHTML = items.length ? items.map(([c, v]) => `<button data-add="${esc(c)}"><b>${esc(c)}</b><span>${esc(v.title)}</span><span class="${mine.has(c) ? "on" : ""}">${mine.has(c) ? "Added" : esc(`${wk(v.date)} ${dn(v.date)}, ${v.time.split("-")[0]}`)}</span></button>`).join("") : `<p class="empty">No course matches “${esc(q)}”.</p>`;
}
function openPicker() { if (!state.id) { input.focus(); return; } $("#pSearch").value = ""; drawPicker(); picker.showModal(); $("#pSearch").focus(); }
$("#pSearch").addEventListener("input", drawPicker);
$("#pClose").addEventListener("click", () => picker.close());
picker.addEventListener("click", (e) => { if (e.target === picker) picker.close(); });

/* ---------- catalogue ---------- */
let day = "";
function drawCat() {
  const q = $("#catFilter").value.toLowerCase().trim();
  const mine = new Set(state.id ? schedule(state.id).all.map((e) => e.c) : []);
  const items = Object.entries(CAT).filter(([c, v]) => (!day || v.date === day) && (!q || (c + " " + v.title + " " + (v.also || []).join(" ")).toLowerCase().includes(q)))
    .sort((a, b) => a[1].date === b[1].date ? mins(a[1].time) - mins(b[1].time) || a[0].localeCompare(b[0]) : a[1].date < b[1].date ? -1 : 1);
  $("#catCount").textContent = `${items.length} of ${Object.keys(CAT).length} courses`;
  $("#catList").innerHTML = items.map(([c, v]) => `<div class="row"><b>${wk(v.date)} ${dn(v.date)}</b><span class="t">${esc(v.time.replace("-", " to "))}</span><span><b class="${mine.has(c) ? "mine" : ""}">${esc(c)}${(v.also || []).length ? " / " + esc(v.also.join(" / ")) : ""}</b> ${esc(v.title)}</span><span class="r">${esc((v.rooms || []).join(", ") || "Room not listed")}</span></div>`).join("") || `<p class="empty">Nothing matches. Try a course code like MATH 101.</p>`;
  $("#catDays").innerHTML = [["", "All days"], ...DAYS.map((d) => [d, `${wk(d)} ${dn(d)}`])].map(([d, l]) => `<button data-day="${d}" aria-pressed="${d === day}">${l}</button>`).join("");
}
function toggleCat(force) {
  const el = $("#catalog"), show = force ?? el.hidden;
  el.hidden = !show; $("#navAll").setAttribute("aria-pressed", show);
  if (show) { drawCat(); el.scrollIntoView({ behavior: "smooth" }); }
}
$("#catFilter").addEventListener("input", drawCat);
$("#navAll").addEventListener("click", () => toggleCat());
$("#navPrint").addEventListener("click", () => window.print());

/* ---------- clear + copy link ---------- */
$("#clear").addEventListener("click", () => { input.value = ""; paint(); submit(); input.focus(); });
const toastEl = $("#toast"); let tt;
function toast(m) { toastEl.textContent = m; toastEl.classList.add("show"); clearTimeout(tt); tt = setTimeout(() => toastEl.classList.remove("show"), 2200); }
async function copyLink(btn) {
  const url = location.href;
  try { await navigator.clipboard.writeText(url); }
  catch {
    const t = document.createElement("textarea"); t.value = url; t.style.cssText = "position:fixed;opacity:0"; document.body.appendChild(t); t.select();
    let ok = false; try { ok = document.execCommand("copy"); } catch {} t.remove();
    if (!ok) return toast(url);
  }
  toast("Link copied");
  if (btn) { const old = btn.textContent; btn.textContent = "Copied"; setTimeout(() => (btn.textContent = old), 1600); }
}

/* ---------- events ---------- */
document.addEventListener("click", (e) => {
  const t = e.target.closest("button"); if (!t) return;
  if (t.dataset.id) { setId(t.dataset.id); $("#results").scrollIntoView({ behavior: "smooth" }); }
  else if (t.dataset.go) {
    const el = document.getElementById("x-" + t.dataset.go.replace(/\W/g, "_"));
    if (el) { el.scrollIntoView({ behavior: "smooth", block: "center" }); el.classList.add("hl"); setTimeout(() => el.classList.remove("hl"), 1800); }
  }
  else if ("copy" in t.dataset) copyLink(t);
  else if ("open" in t.dataset) openPicker();
  else if (t.dataset.prog) { store.set(`mf:prog:${state.id}`, t.dataset.prog); render(state.id); }
  else if (t.dataset.remove) { store.set(`mf:added:${state.id}`, store.get(`mf:added:${state.id}`, []).filter((c) => primary(c) !== t.dataset.remove)); render(state.id); }
  else if (t.dataset.add) {
    const k = `mf:added:${state.id}`, cur = store.get(k, []), c = primary(t.dataset.add);
    store.set(k, cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c]); drawPicker(); render(state.id);
  }
  else if ("day" in t.dataset) { day = t.dataset.day; drawCat(); }
});
document.addEventListener("change", (e) => {
  const s = e.target.closest("select[data-slot]"); if (!s) return;
  const k = `mf:slots:${state.id}`; store.set(k, { ...store.get(k, {}), [s.dataset.slot]: s.value }); render(state.id);
});
document.addEventListener("keydown", (e) => { if (e.key === "/" && !/INPUT|SELECT/.test(document.activeElement.tagName) && !picker.open) { e.preventDefault(); input.focus(); } });

const ids = Object.keys(S).length;
$("#stats").textContent = `${ids.toLocaleString()} students, ${Object.values(S).reduce((n, l) => n + l.length, 0).toLocaleString()} seat assignments, ${Object.keys(CAT).length} courses.`;
paint();
const q = new URLSearchParams(location.search).get("id");
if (q && /^\d{9}$/.test(q)) setId(q); else paint();
})();
