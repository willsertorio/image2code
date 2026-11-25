#!/usr/bin/env python3
"""Build rubrics/index.html from rubrics.json, human.json, carbon.json and the captures.

Run from anywhere:  python3 rubrics/build.py
The data is embedded in the page at build time, so the page makes no runtime fetches.
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, default):
    p = os.path.join(HERE, name)
    return json.load(open(p)) if os.path.exists(p) else default


R = load("rubrics.json", None)
HUMAN = load("human.json", {})
CARBON = load("carbon.json", {})
NOTES = load("notes.json", {})

samples = []
for s in R["samples"]:
    sid = s["id"]
    h, c = HUMAN.get(sid, {}), CARBON.get(sid, {})
    rows = []
    for k in s["criteria"]:
        hv, cv = h.get(k["n"], {}), c.get(k["n"], {})
        rows.append({"n": k["n"], "d": k["d"], "c": k["c"],
                     "h": hv.get("pass"), "hc": hv.get("comment", ""),
                     "j": cv.get("pass"), "jc": cv.get("comment", "")})
    model = f"samples/{sid}/model.html"
    caps = sorted(os.path.relpath(p, HERE) for p in glob.glob(os.path.join(HERE, "captures", sid, "*.jpg")))
    samples.append({"id": sid, "name": s["name"], "ref": f"img/{sid}.jpg", "thumb": f"img/{sid}_thumb.jpg",
                    "model": model if os.path.exists(os.path.join(HERE, model)) else None,
                    "caps": caps, "rows": rows, "note": NOTES.get(sid, "")})

ICON_BOOK = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 7v14"/><path d="M16 12h2"/><path d="M16 8h2"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/><path d="M6 12h2"/><path d="M6 8h2"/></svg>'
ICON_BOX = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/></svg>'
ICON_BACK = '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>'

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Image2Code Rubrics</title>
<link rel="stylesheet" href="../css/docs.css">
<style>
.side { display: flex; flex-direction: column; }
.side .back { margin-top: auto; border: 1px solid var(--line); }
@media (max-width: 760px) { .side { flex-direction: row; } .side .back { margin-top: 0; margin-left: 8px; flex: none; } .side .back span { display: none; } }
.refs-label { margin: 24px 0 8px; }
.refs { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.refs a { text-decoration: none; display: block; color: var(--ink); min-width: 0; }
.refs img { display: block; width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); }
.refs a:hover img { border-color: #4A4A4A; }
.refs .label { display: block; margin-top: 6px; }
@media (max-width: 767px) { .refs { grid-template-columns: repeat(3, 1fr); } }
.doc p.note { color: var(--ink-2); margin: 0 0 4px; max-width: 68ch; }
.prompt { display: flex; gap: 14px; align-items: center; margin: 16px 0 20px; padding: 12px 14px; background: var(--side); border: 1px solid var(--line); border-radius: 8px; }
.prompt img { width: 52px; height: 52px; object-fit: cover; border-radius: 6px; flex: none; }
.prompt p { margin: 4px 0 0; font-size: 15px; color: var(--ink); }
.pair { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 1100px) { .pair { grid-template-columns: 1fr; } }
.pair figure { margin: 0; min-width: 0; }
.ref-frame { aspect-ratio: 16 / 9; border-radius: 8px; border: 1px solid var(--line); background: #04070A; display: grid; place-items: center; overflow: hidden; }
.ref-frame img { width: 100%; height: 100%; max-width: 100%; object-fit: contain; }
.caps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 12px; }
.caps a { display: block; text-decoration: none; min-width: 0; }
.caps img { display: block; width: 100%; aspect-ratio: 16 / 10; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); }
.caps .label { display: block; margin-top: 6px; }
@media (max-width: 479px) { .caps { grid-template-columns: 1fr 1fr; } }
.gen-note { margin: 12px 0 0; color: var(--ink-2); max-width: 68ch; }
table.rubric td.n { white-space: nowrap; }
table.rubric td.mono { font: 400 12.5px/1.6 var(--mono); color: var(--ink-2); white-space: nowrap; }
table.rubric tr.gate td { background: rgba(63, 140, 232, .06); }
table.rubric tr.dis td { background: rgba(248, 113, 113, .07); }
table.rubric tr.dis td:first-child { box-shadow: inset 2px 0 0 #F87171; }
table.rubric.judge td.c { text-align: center; white-space: nowrap; }
table.rubric.judge th:nth-child(2), table.rubric.judge th:nth-child(3) { width: 84px; text-align: center; }
table.rubric.judge th:first-child { width: 34%; }
.legend { display: flex; gap: 16px; margin: 12px 0 0; flex-wrap: wrap; }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 9px; height: 9px; border-radius: 2px; display: inline-block; }
.page-filter { display: inline-flex; align-items: center; gap: 8px; margin: 12px 0 0; cursor: pointer; }
.only-dis tr.agree { display: none; }
.frame .loading { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; background: #04070A; transition: opacity .4s ease; pointer-events: none; }
.frame .loading.done { opacity: 0; }
.frame .spin { width: 24px; height: 24px; border-radius: 50%; border: 2px solid #2A2A2A; border-top-color: var(--ink-2); animation: spin .9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .frame .spin { animation-duration: 2.4s; } }
</style>
</head>
<body>
<nav class="side" aria-label="Pages">
  <a href="#overview" data-id="overview">__ICON_BOOK__<span>Overview</span></a>
  <span class="group">Samples</span>
  <span id="menu" style="display:contents"></span>
  <a class="back" href="../">__ICON_BACK__<span>Image2Code samples</span></a>
</nav>
<main class="main"><article class="doc" id="page"></article></main>
<script>
// Built by rubrics/build.py from rubrics.json, human.json, carbon.json and the captures.
const PROMPT = __PROMPT__;
const MODEL = __MODEL__;
const SAMPLES = __SAMPLES__;
const ICON_BOX = '__ICON_BOX__';
const page = document.getElementById('page');
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const mark = v => v === true ? '<span class="yes" aria-label="Pass">&#10003;</span>' : v === false ? '<span class="no" aria-label="Fail">&#10007;</span>' : '<span class="na" aria-label="Not scored">&ndash;</span>';
const passes = (rows, k) => rows.some(r => r[k] !== null && r[k] !== undefined) ? `${rows.filter(r => r[k] === true).length} / ${rows.length}` : '&ndash;';
const both = r => typeof r.h === 'boolean' && typeof r.j === 'boolean';
const agreeText = rows => { const b = rows.filter(both); return b.length ? `${b.filter(r => r.h === r.j).length} / ${b.length}` : '&ndash;'; };
const capName = p => p.split('/').pop().replace(/^\\d+_/, '').replace('.jpg', '').replace(/_/g, ' ');

document.getElementById('menu').innerHTML = SAMPLES.map(s => `<a href="#${s.id}" data-id="${s.id}">${ICON_BOX}<span>${esc(s.name)}</span></a>`).join('');

function renderOverview() {
  const all = SAMPLES.flatMap(s => s.rows);
  const cats = [];
  all.forEach(r => { if (!cats.includes(r.d)) cats.push(r.d); });
  const catRows = cats.map(d => {
    const rs = all.filter(r => r.d === d), b = rs.filter(both);
    return `<tr><td>${esc(d)}</td><td class="mono">${rs.length}</td><td class="mono">${passes(rs, 'h')}</td><td class="mono">${passes(rs, 'j')}</td><td class="mono">${b.length ? Math.round(100 * b.filter(r => r.h === r.j).length / b.length) + '%' : '&ndash;'}</td></tr>`;
  }).join('');
  const results = SAMPLES.map(s => `<tr><td><a href="#${s.id}" style="text-decoration:none">${esc(s.name)}</a></td><td class="mono">${s.rows.length}</td><td class="mono">${passes(s.rows, 'h')}</td><td class="mono">${passes(s.rows, 'j')}</td><td class="mono">${agreeText(s.rows)}</td></tr>`).join('');
  page.className = 'doc';
  page.innerHTML = `
    <h1 class="home">Rubrics</h1>
    <p class="lead">Five photos, each turned into a 3D scene by ${esc(MODEL)} from one prompt, then scored against its rubric twice: by a human review and by ${esc(MODEL)} as a judge.</p>
    <div class="label refs-label">Reference images</div>
    <div class="refs">${SAMPLES.map(s => `<a href="#${s.id}"><img src="${esc(s.thumb)}" alt="Reference photo: ${esc(s.name)}" loading="lazy"><span class="label">${esc(s.name)}</span></a>`).join('')}</div>
    <h2>Results</h2>
    <div class="table-wrap"><table class="rubric plain"><thead><tr><th>Sample</th><th>Criteria</th><th>Human</th><th>Carbon</th><th>Agree</th></tr></thead><tbody>${results}</tbody></table></div>
    <h2>By category</h2>
    <div class="table-wrap"><table class="rubric plain"><thead><tr><th>Category</th><th>Criteria</th><th>Human</th><th>Carbon</th><th>Agree</th></tr></thead><tbody>${catRows}</tbody></table></div>`;
}

function rubricTable(rows) {
  const order = [];
  rows.forEach(r => { if (!order.includes(r.d)) order.push(r.d); });
  const body = order.map(d => `<tr class="grp"><th colspan="4">${esc(d)}</th></tr>` + rows.filter(r => r.d === d).map(r => {
    const dis = both(r) && r.h !== r.j;
    const cls = [dis ? 'dis' : 'agree', r.n.startsWith('G') ? 'gate' : ''].join(' ');
    const cm = (r.hc ? `<p class="cl"><span class="src">Human</span> ${esc(r.hc)}</p>` : '') + (r.jc ? `<p class="cl"><span class="src">Carbon</span> ${esc(r.jc)}</p>` : '');
    return `<tr class="${cls}"><td><strong>${esc(r.n)}</strong> &mdash; ${esc(r.c)}</td><td class="c">${mark(r.h)}</td><td class="c">${mark(r.j)}</td><td class="cm">${cm}</td></tr>`;
  }).join('')).join('');
  return `<div class="legend label"><span><i style="background:rgba(63,140,232,.5)"></i>Gate</span><span><i style="background:rgba(248,113,113,.6)"></i>Disagreement</span></div>
    <label class="page-filter label"><input type="checkbox" class="only-dis-box"> Show disagreements only</label>
    <div class="table-wrap judge-wrap"><table class="rubric merged judge"><thead><tr><th>Rubric</th><th>Human</th><th>Carbon</th><th>Comments</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderSample(s) {
  page.className = 'doc wide';
  const scene = s.model
    ? `<div class="frame"><iframe data-src="${esc(s.model)}" title="${esc(MODEL)} scene" allow="fullscreen" allowfullscreen></iframe><div class="loading" aria-live="polite"><span class="spin" aria-hidden="true"></span><span class="label">Loading</span></div></div>`
    : `<div class="frame"><div class="pending">Scene pending</div></div>`;
  page.innerHTML = `
    <header class="title-row"><div><h1>${esc(s.name)}</h1><div class="label">${s.rows.length} criteria &middot; Human ${passes(s.rows, 'h')} &middot; Carbon ${passes(s.rows, 'j')}</div></div></header>
    <div class="prompt"><img src="${esc(s.thumb)}" alt="Reference photo sent with the prompt"><div><div class="label">Prompt &middot; sent with the reference photo</div><p>${esc(PROMPT)}</p></div></div>
    <section class="pair">
      <figure class="pane"><div class="pane-head"><span class="label">${esc(MODEL)}</span>${s.model ? `<a href="${esc(s.model)}" target="_blank" rel="noopener">Open full screen</a>` : ''}</div>${scene}</figure>
      <figure class="pane"><div class="pane-head"><span class="label">Reference photo</span><a href="${esc(s.ref)}" target="_blank" rel="noopener">Open full size</a></div><div class="ref-frame"><img src="${esc(s.ref)}" alt="Reference photo: ${esc(s.name)}"></div></figure>
    </section>
    ${s.note ? `<p class="gen-note">${esc(s.note)}</p>` : ''}
    ${s.caps.length ? `<details class="sec"><summary><h2>Captures</h2><span class="label">${s.caps.length} views &middot; what both reviews saw</span></summary><div class="caps">${s.caps.map(c => `<a href="${esc(c)}" target="_blank" rel="noopener"><img src="${esc(c)}" alt="${esc(capName(c))}" loading="lazy"><span class="label">${esc(capName(c))}</span></a>`).join('')}</div></details>` : ''}
    <details class="sec" open><summary><h2>Rubrics</h2><span class="label">${agreeText(s.rows)} agree</span></summary>${rubricTable(s.rows)}</details>`;
  page.querySelectorAll('.only-dis-box').forEach(b => b.addEventListener('change', () => page.querySelector('.judge-wrap').classList.toggle('only-dis', b.checked)));
  page.querySelectorAll('.frame iframe[data-src]').forEach(f => {
    const cover = f.parentElement.querySelector('.loading');
    f.addEventListener('load', () => { if (f.src && f.src !== 'about:blank') setTimeout(() => cover.classList.add('done'), 600); });
    f.src = f.dataset.src;
  });
}

function render() {
  const id = location.hash.slice(1);
  const s = SAMPLES.find(x => x.id === id);
  document.querySelectorAll('.side a[data-id]').forEach(a => { if (a.dataset.id === (s ? s.id : 'overview')) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  if (s) renderSample(s); else renderOverview();
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', render);
render();
</script>
</body>
</html>
"""

html = (PAGE.replace("__ICON_BOOK__", ICON_BOOK).replace("__ICON_BACK__", ICON_BACK).replace("__ICON_BOX__", ICON_BOX)
        .replace("__PROMPT__", json.dumps(R["prompt"]))
        .replace("__MODEL__", json.dumps("Gemini 4 Carbon"))
        .replace("__SAMPLES__", json.dumps(samples, ensure_ascii=False)))
open(os.path.join(HERE, "index.html"), "w").write(html)
print(f"wrote rubrics/index.html: {len(samples)} samples, "
      f"{sum(1 for s in samples for r in s['rows'] if r['h'] is not None)} human and "
      f"{sum(1 for s in samples for r in s['rows'] if r['j'] is not None)} Carbon verdicts")
