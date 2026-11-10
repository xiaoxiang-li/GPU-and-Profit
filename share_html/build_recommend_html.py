#!/usr/bin/env python3 -I
"""Build share_html/GPU-LLM-Recommend.html — mirror of notebook §2
(recommendation panel / c7_run). Three modes:
  • All 5 models (aggregated)     → ranked full table + per-model rollup
  • one specific model            → ranked table + suggested token prices
  • Mine − Public per GPU          → margin-edge comparison
No chart; all logic 1:1 from the notebook cell."""

import json, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT  = os.path.join(HERE, 'GPU-LLM-Recommend.html')

def _find(name):
    for d in [os.path.join(ROOT, 'colab_upload', 'GPU-LLM-v2-Analytics-Colab 6'),
              os.path.join(ROOT, 'colab_upload'),
              os.path.join(ROOT, 'grid'),
              os.path.join(ROOT, 'data')]:
        p = os.path.join(d, name)
        if os.path.exists(p): return p
    raise FileNotFoundError(name)

# §2 needs the FULL grid rows (not just unique options) because its d-dedup
# keeps (option_id, gpu_class, price_src, model, mix, throughput_case).
grid = pd.read_csv(_find('grid_full_v2.csv'))
keep = ['option_id','model','mix','throughput_case','gpu_class','rental_term',
        'listed_rate','eff_cost_ph','price_src','perf_src']
grid_slim = grid[keep].drop_duplicates().copy()
for c in ['listed_rate','eff_cost_ph']:
    grid_slim[c] = grid_slim[c].astype(float)

PAYLOAD = {
    "PRICES": {"glm-5.3-flash": dict(pin=.15, pca=.03, pou=.50),
               "kimi-k3":       dict(pin=3.,  pca=.30, pou=15.),
               "deepseek-v4.1-flash": dict(pin=.15, pca=.003, pou=.60),
               "hy4-preview":   dict(pin=.80, pca=.038, pou=2.48),
               "mimo-v2.6-flash": dict(pin=.14, pca=.003, pou=.28)},
    "HW_SCALE": {"glm-5.3-flash": {"b300":1.,"gb300":1.12,"b200":.454,"gb200":.187,
                                   "h200":.049,"mi355x":.493,"mi325x":.026,"h100":.041},
                 "kimi-k3":       {"b300":1.,"gb300":5.877,"b200":.988,"gb200":1.068,
                                   "h200":.012,"mi355x":1.213,"mi325x":.669,"h100":.063},
                 "deepseek-v4.1-flash": {"b300":1.,"gb300":5.936,"b200":.883,"gb200":.831,
                                         "h200":.159,"mi355x":.426,"mi325x":.090,"h100":.041},
                 "hy4-preview":   {"b300":1.,"gb300":1.132,"b200":.801,"gb200":.801,
                                   "h200":.215,"mi355x":.878,"mi325x":0.,"h100":0.},
                 "mimo-v2.6-flash":{"b300":1.,"gb300":1.,"b200":.6,"gb200":.55,
                                    "h200":.1,"mi355x":.5,"mi325x":.08,"h100":.06}},
    "GATES": {"25000": {"60":{"128":[21957.5,112.4],"256":[19472.5,199.4],"512":[21998.,450.5],"1024":[5707.5,233.7]},
                        "90":{"128":[52767.5,270.2],"256":[34350.,351.7],"512":[10750.,220.1],"1024":[2905.,119.]},
                        "92":{"128":[46405.,237.6],"256":[35470.,363.2],"512":[18957.5,388.3],"1024":[4917.5,201.5]}},
              "13000": {"60":{"128":[20718.1,204.],"256":[18848.7,371.2],"512":[10095.8,397.6],"1024":[3006.9,236.8]},
                        "89":{"128":[33507.5,329.9],"256":[31311.8,616.6],"512":[18250.7,718.8],"1024":[3181.1,250.6]}}},
    "ANCHOR": {"kimi-k3":            {"in_tps":12479., "out_tps":87.6},
               "deepseek-v4.1-flash": {"in_tps":441986., "out_tps":3170.5},
               "hy4-preview":        {"in_tps":54484., "out_tps":379.4},
               "mimo-v2.6-flash":    {"in_tps":33629., "out_tps":250.}},
    "KV_GAIN_PTS": {"60,128":1.00,"60,256":1.00,"60,512":1.00,"60,1024":1.00,
                    "90,128":2.40,"90,256":1.76,"90,512":0.87,"90,1024":0.51},
    "KV_GAIN_MODEL_PRIOR": {"kimi-k3":1.30, "deepseek-v4.1-flash":1.00,
                            "hy4-preview":1.00, "mimo-v2.6-flash":0.50},
    "MIX_FRACTIONS": {"agentic": {"fresh":0.34, "cached":0.65, "out":0.01},
                      "chatisy": {"fresh":0.55, "cached":0.20, "out":0.25}},
    "CLASS_WEIGHT":  {"fresh":1.0, "cached":0.20, "out":1.0},
    "SUG_MARGIN_TIERS": [["30", 0.30], ["50", 0.50], ["70", 0.70]],
    "PUBLIC_PRICE_LIST": {
        "glm-5.3-flash":       {"fresh":0.15, "cached":0.03,  "out":0.50, "ref":"OpenRouter GLM-5.2 listing"},
        "kimi-k3":             {"fresh":3.00, "cached":0.30,  "out":15.00,"ref":"Moonshot official rate card"},
        "deepseek-v4.1-flash": {"fresh":0.15, "cached":0.003, "out":0.60, "ref":"DeepSeek Day-6 report / OpenRouter"},
        "hy4-preview":         {"fresh":0.80, "cached":0.038, "out":2.48, "ref":"OpenRouter Hy4 preview listing"},
        "mimo-v2.6-flash":     {"fresh":0.14, "cached":0.003, "out":0.28, "ref":"eesel.ai V2.6 / OpenRouter (2026-10-28 input $0.10→$0.14)"},
    },
    "WORKLOADS": [
        ["agentic · ISL 25k · OSL 512 · KV 60%",  ["agentic",  25000, 512, 60]],
        ["agentic · ISL 25k · OSL 128 · KV 90%",  ["agentic",  25000, 128, 90]],
        ["agentic · ISL 25k · OSL 1024 · KV 60%", ["agentic",  25000, 1024, 60]],
        ["agentic · ISL 13k · OSL 512 · KV 60%",  ["agentic",  13000, 512, 60]],
        ["agentic · ISL 13k · OSL 256 · KV 89%",  ["agentic",  13000, 256, 89]],
        ["chat · ISL 4k · OSL 128 · KV 40%",      ["chatisy",   4000, 128, 40]],
        ["chat · ISL 1k · OSL 128 · KV 60%",      ["chatisy",   1000, 128, 60]],
    ],
    "MODELS_5":   sorted(grid['model'].unique().tolist()),
    "PRICE_SRCS": sorted(grid['price_src'].unique().tolist()),
    "GPUS_ALL":   sorted(grid['gpu_class'].unique().tolist()),
    "GRID":       grid_slim.to_dict(orient='records'),
}

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recommend — GPU LLM</title>
<style>
  :root { --ink:#0f172a; --ink-2:#475569; --ink-3:#64748b; --line:#e2e8f0;
          --surface:#fff; --surface-2:#f8fafc; --good:#059669; --warn:#d97706; --bad:#dc2626;
          --accent:#0ea5e9; }
  * { box-sizing:border-box }
  body { margin:0; padding:0; background:#f1f5f9; color:var(--ink);
         font:14px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:1280px; margin:24px auto; padding:0 20px 40px; }
  h1 { font-size:17px; margin:0 0 4px; }
  .sub { color:var(--ink-3); font-size:12px; margin-bottom:18px; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin-bottom:14px; box-shadow:0 1px 2px rgba(15,23,42,.04); }
  .row { display:flex; flex-wrap:wrap; gap:10px 14px; align-items:flex-end; }
  .fld { display:flex; flex-direction:column; gap:3px; min-width:118px; }
  .fld > label { font-size:10.5px; font-weight:600; color:var(--ink-3); text-transform:uppercase; letter-spacing:.06em; }
  select, input[type=number] { font:inherit; padding:5px 8px; border:1px solid var(--line);
    border-radius:6px; background:var(--surface); color:var(--ink); }
  input[type=range] { accent-color:var(--accent); padding:0; }
  .w-num { width:90px; }
  .hdr { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
         font-size:11.5px; color:var(--ink-2); white-space:pre-wrap; margin:0 0 10px; }
  .hdr strong { color:var(--ink); }
  table { border-collapse:collapse; width:100%; font-size:12px; }
  thead th { position:sticky; top:0; background:var(--surface-2); color:var(--ink-3);
             font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:.05em;
             padding:7px 10px; text-align:right; border-bottom:1px solid var(--line); cursor:pointer; user-select:none; }
  thead th:hover { color:var(--ink); }
  tbody td { padding:5px 10px; text-align:right; border-top:1px solid #f1f5f9; font-variant-numeric:tabular-nums; }
  tbody tr:hover { background:#f1f9ff }
  td.l, th.l { text-align:left }
  .tblscroll { max-height:520px; overflow:auto; border:1px solid var(--line); border-radius:8px; }
  .pos { color:var(--good); font-weight:600 }
  .neg { color:var(--bad);  font-weight:600 }
  .psz { font-size:10px; padding:1px 6px; border-radius:4px; font-weight:600; }
  .psz.my  { background:#fff4d6; color:#92400e }
  .psz.pub { background:#e8f1fc; color:#1e3a8a }
  .be { background:#fff3cd; font-weight:600 }
  .foot { color:var(--ink-3); font-size:11px; margin-top:8px; }
  h2 { font-size:13px; font-weight:700; margin:14px 0 6px; color:var(--ink); }
</style></head>
<body><div class="wrap">
  <h1>Recommendation panel</h1>
  <div class="sub">§2 mirror from <code>GPU-LLM-v2-Analytics.ipynb</code> — pick a mode, see the best-ranked offers. Prices update on input.</div>

  <div class="card">
    <div class="row">
      <div class="fld"><label>Mode / model</label>
        <select id="w_model">
          <option value="__all__" selected>All 5 models (aggregated)</option>
          <option value="__compare__">Mine − Public per GPU · your margin edge</option>
        </select></div>
      <div class="fld"><label>Price source</label><select id="w_price"></select></div>
      <div class="fld"><label>GPU class</label><select id="w_gpu"></select></div>
      <div class="fld"><label>Workload</label><select id="w_work"></select></div>
      <div class="fld" style="min-width:200px"><label>GPU utilisation % · <span id="v_util">100</span></label>
        <input type="range" id="w_util" min="10" max="100" step="5" value="100"></div>
    </div>
  </div>

  <div class="card">
    <div id="cmp_banner" class="hdr" style="display:none"></div>
    <div id="sugg_block" style="display:none">
      <h2 id="sugg_title"></h2>
      <div id="sugg_sub" class="hdr" style="margin:0 0 8px"></div>
      <div class="tblscroll" style="max-height:none"><table id="sugg_tbl"></table></div>
    </div>
    <div id="rollup_block" style="display:none">
      <h2>Per-model rollup</h2>
      <div class="tblscroll" style="max-height:none"><table id="rollup_tbl"></table></div>
    </div>
    <div id="main_block">
      <div class="hdr" id="hd"></div>
      <div class="tblscroll"><table id="main_tbl"></table></div>
      <div class="foot" id="ft"></div>
    </div>
  </div>
</div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
'use strict';
const P = JSON.parse(document.getElementById('payload').textContent);
const $ = id => document.getElementById(id);

// maths, ported 1:1 from notebook
function kvGainAt(kv, osl, strength=1) {
  const pts = P.KV_GAIN_PTS;
  const kvs  = [...new Set(Object.keys(pts).map(k => +k.split(',')[0]))].sort((a,b)=>a-b);
  const osls = [...new Set(Object.keys(pts).map(k => +k.split(',')[1]))].sort((a,b)=>a-b);
  const kvC  = Math.max(kvs[0], Math.min(kv, kvs[kvs.length-1]));
  const oslC = Math.max(osls[0],Math.min(osl,osls[osls.length-1]));
  const kvLo = Math.max(...kvs.filter(k=>k<=kvC));
  const kvHi = Math.min(...kvs.filter(k=>k>=kvC));
  const oslLo= Math.max(...osls.filter(o=>o<=oslC));
  const oslHi= Math.min(...osls.filter(o=>o>=oslC));
  const f11=pts[`${kvLo},${oslLo}`], f12=pts[`${kvLo},${oslHi}`];
  const f21=pts[`${kvHi},${oslLo}`], f22=pts[`${kvHi},${oslHi}`];
  const tx = kvHi===kvLo ? 0 : (kvC-kvLo)/(kvHi-kvLo);
  const ty = oslHi===oslLo? 0 : (oslC-oslLo)/(oslHi-oslLo);
  const raw = f11*(1-tx)*(1-ty) + f21*tx*(1-ty) + f12*(1-tx)*ty + f22*tx*ty;
  return 1 + (raw-1)*strength;
}
function anchorsFor(model, isl, osl, kv) {
  if (model==='glm-5.3-flash') {
    const g = P.GATES[isl] || P.GATES['25000'];
    const kvs = Object.keys(g).map(Number).sort((a,b)=>a-b);
    const kvUse = kv>=kvs[kvs.length-1]?kvs[kvs.length-1]:(kv<=kvs[0]?kvs[0]:Math.max(...kvs.filter(k=>k<=kv)));
    const tbl = g[String(kvUse)];
    const osls = Object.keys(tbl).map(Number).sort((a,b)=>a-b);
    const cap = Math.min(osl, osls[osls.length-1]);
    const anch = Math.max(...osls.filter(o=>o<=cap));
    const [it, ot] = tbl[String(anch)];
    return {inA:it, outA:ot, gain:1};
  }
  const a = P.ANCHOR[model];
  const prior = P.KV_GAIN_MODEL_PRIOR[model];
  const gain = kvGainAt(kv, osl, prior);
  return {inA:a.in_tps*gain, outA:a.out_tps*gain, gain};
}

// populate dropdowns
{
  const msel = $('w_model');
  for (const m of P.MODELS_5) {
    const o = document.createElement('option'); o.value=m; o.textContent=m; msel.appendChild(o);
  }
  const psel = $('w_price');
  for (const [v,l] of [['__all__','all'], ...P.PRICE_SRCS.map(s=>[s,s])]) {
    const o = document.createElement('option'); o.value=v; o.textContent=l; psel.appendChild(o);
  }
  const gsel = $('w_gpu');
  for (const [v,l] of [['__all__','all'], ...P.GPUS_ALL.map(g=>[g,g.toUpperCase()])]) {
    const o = document.createElement('option'); o.value=v; o.textContent=l; gsel.appendChild(o);
  }
  const wsel = $('w_work');
  P.WORKLOADS.forEach(([lbl, val]) => {
    const o = document.createElement('option');
    o.value = JSON.stringify(val); o.textContent = lbl; wsel.appendChild(o);
  });
}

let sortKey = 'profit_ph', sortDir = -1;
function mkHeader(tableEl, cols) {
  tableEl.innerHTML = '<thead><tr>' + cols.map(c =>
    `<th class="${c.align==='l'?'l':''}" data-k="${c.key}">${c.label}</th>`).join('') + '</tr></thead><tbody></tbody>';
  tableEl.querySelectorAll('th').forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.k;
    if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = -1; }
    render();
  }));
}
const fmtUsd = (v,d=2) => (v==null||isNaN(v)) ? '—' : '$'+Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const fmtSgn = (v,d=2) => (v==null||isNaN(v)) ? '—' : (v>=0?'+':'-')+'$'+Math.abs(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});

function render() {
  const selModel = $('w_model').value;
  const selPrice = $('w_price').value;
  const selGpu   = $('w_gpu').value;
  const workJson = $('w_work').value;
  const [mix, isl, osl, kv] = JSON.parse(workJson);
  const UTIL = +$('w_util').value / 100;
  $('v_util').textContent = Math.round(UTIL*100);

  const mixFrac = P.MIX_FRACTIONS[mix];

  // shared filter
  let d = P.GRID.slice();
  if (selModel !== '__all__' && selModel !== '__compare__') d = d.filter(r => r.model === selModel);
  if (selPrice !== '__all__') d = d.filter(r => r.price_src === selPrice);
  if (selGpu   !== '__all__') d = d.filter(r => r.gpu_class === selGpu);
  d = d.filter(r => r.mix === mix && r.throughput_case === 'best');
  // dedupe as notebook does
  const seen = new Set();
  d = d.filter(r => {
    const key = [r.option_id, r.gpu_class, r.price_src, r.model, r.mix, r.throughput_case].join('|');
    if (seen.has(key)) return false; seen.add(key); return true;
  });

  const cmpMode = selModel === '__compare__';
  const allMode = selModel === '__all__';
  $('cmp_banner').style.display = cmpMode ? 'block' : 'none';
  $('rollup_block').style.display = allMode ? 'block' : 'none';
  $('sugg_block').style.display = (allMode || cmpMode) ? 'none' : 'block';
  $('main_block').style.display = cmpMode ? 'none' : 'block';

  // per-row economics recomputed for current workload
  for (const r of d) {
    const { inA, outA } = anchorsFor(r.model, isl, osl, kv);
    const hw = P.HW_SCALE[r.model][r.gpu_class] || 0;
    r._in_t = inA * hw;   r._out_t = outA * hw;
    const fsh = r._in_t * mixFrac.fresh / Math.max(mixFrac.fresh + mixFrac.cached, 1e-9);
    const cch = r._in_t * mixFrac.cached / Math.max(mixFrac.fresh + mixFrac.cached, 1e-9);
    const prices = P.PRICES[r.model];
    r.revenue_ph = (fsh*prices.pin + cch*prices.pca + r._out_t*prices.pou) * 3600/1e6;
    r.profit_ph  = r.revenue_ph * UTIL - r.eff_cost_ph;
    r.margin_pct = (r.revenue_ph * UTIL) ? r.profit_ph / (r.revenue_ph * UTIL) * 100 : NaN;
    r.be_lower   = r.eff_cost_ph / r.revenue_ph;
    r.be_upper   = r.be_lower * 1.6;
    r.mixed_tps  = r._in_t + r._out_t;
  }

  if (cmpMode) {
    // compare my vs public per gpu
    const a = {}, b = {};
    for (const r of d) {
      if (r.price_src === 'my_quotes') {
        if (!(r.gpu_class in a) || r.profit_ph > a[r.gpu_class]) a[r.gpu_class] = r.profit_ph;
      } else if (r.price_src === 'public_market') {
        if (!(r.gpu_class in b) || r.profit_ph > b[r.gpu_class]) b[r.gpu_class] = r.profit_ph;
      }
    }
    const gpus = [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();
    const rows = gpus.map(g => ({gpu: g.toUpperCase(),
                                  mine: a[g], pub: b[g],
                                  delta: (a[g]!=null && b[g]!=null) ? a[g]-b[g] : null}))
                     .sort((x,y) => (y.delta ?? -1e9) - (x.delta ?? -1e9));
    const tbl = $('main_tbl');
    mkHeader(tbl, [
      {key:'gpu',   label:'GPU',       align:'l'},
      {key:'mine',  label:'my best profit $/GPU·h'},
      {key:'pub',   label:'public best $/GPU·h'},
      {key:'delta', label:'Δ (mine − public)'},
    ]);
    const tb = tbl.querySelector('tbody'); tb.innerHTML='';
    for (const r of rows) {
      const tr = document.createElement('tr');
      const cls = r.delta==null?'':(r.delta>=0?'pos':'neg');
      tr.innerHTML = `<td class="l">${r.gpu}</td><td>${fmtUsd(r.mine)}</td><td>${fmtUsd(r.pub)}</td>
                      <td class="${cls}">${r.delta==null?'—':fmtSgn(r.delta)}</td>`;
      tb.appendChild(tr);
    }
    $('main_block').style.display = 'block';
    $('hd').textContent = `mine − public best-profit per GPU  ·  mix=${mix}  ·  isl=${isl.toLocaleString()}  osl=${osl}  kv=${kv}%`;
    $('ft').textContent = '';
    return;
  }

  // ─── main ranked table ───
  const mainCols = [
    {key:'model',    label:'model', align:'l'},
    {key:'option_id',label:'offer', align:'l'},
    {key:'gpu_class',label:'gpu',   align:'l'},
    {key:'rental_term',label:'term'},
    {key:'listed_rate', label:'list $/h', fmt: v=>fmtUsd(v,2)},
    {key:'mixed_tps', label:'mixed t/s', fmt: v=>v==null?'—':Math.round(v).toLocaleString()},
    {key:'revenue_ph', label:'rev $/h', fmt: v=>fmtUsd(v,3)},
    {key:'profit_ph', label:'profit $/h', fmt: v=>fmtSgn(v,3)},
    {key:'margin_pct', label:'margin %', fmt: v=>isNaN(v)?'—':v.toFixed(1)+'%'},
    {key:'be_lower',   label:'be lower', fmt: v=>(v*100).toFixed(1)+'%'},
    {key:'be_upper',   label:'be upper', fmt: v=>(v*100).toFixed(1)+'%'},
    {key:'price_src',  label:'src'},
    {key:'perf_src',   label:'perf'},
  ];
  const tblEl = $('main_tbl'); mkHeader(tblEl, mainCols);
  const tb = tblEl.querySelector('tbody'); tb.innerHTML='';
  const rows = d.slice().sort((x,y) => {
    const av = x[sortKey], bv = y[sortKey];
    if (typeof av==='string') return sortDir * String(av).localeCompare(String(bv));
    return sortDir * ((av ?? -Infinity) - (bv ?? -Infinity));
  });
  for (const r of rows) {
    const tr = document.createElement('tr');
    const cls = r.profit_ph>=0?'pos':'neg';
    tr.innerHTML = mainCols.map(c => {
      let v, extra = '';
      if (c.key==='price_src') v = (r.price_src==='my_quotes'?'<span class="psz my">my</span>':'<span class="psz pub">pub</span>');
      else if (c.fmt) v = c.fmt(r[c.key], r);
      else v = r[c.key];
      if (c.key==='profit_ph' || c.key==='median_prof' || c.key==='best_offer') extra = ` class="${cls}"`;
      if (extra && c.align==='l') extra = ` class="${cls} l"`;
      else if (c.align==='l') extra = ' class="l"';
      return `<td${extra}>${v ?? '—'}</td>`;
    }).join('');
    tb.appendChild(tr);
  }
  $('hd').textContent = `mode=${selModel}  ·  workload  mix=${mix}  isl=${isl.toLocaleString()} osl=${osl} kv=${kv}%  ·  utilisation ${(UTIL*100).toFixed(0)}%  ·  showing ${rows.length.toLocaleString()} rows`;
  $('ft').textContent = rows.length ? 'click any column to re-sort' : 'no rows for this combination';

  // ─── per-model rollup (only in __all__) ───
  if (allMode) {
    const per = {};
    for (const r of d) {
      per[r.model] = per[r.model] || {profits: [], margins: []};
      per[r.model].profits.push(r.profit_ph);
      if (!isNaN(r.margin_pct)) per[r.model].margins.push(r.margin_pct);
    }
    const rl = Object.entries(per).map(([m, x]) => ({
      model: m,
      median_prof: x.profits.sort((a,b)=>a-b)[Math.floor(x.profits.length/2)],
      best_offer: Math.max(...x.profits),
      median_margin: x.margins.length ? x.margins.sort((a,b)=>a-b)[Math.floor(x.margins.length/2)] : NaN,
    })).sort((a,b) => b.best_offer - a.best_offer);
    const rt = $('rollup_tbl'); mkHeader(rt, [
      {key:'model', label:'model', align:'l'},
      {key:'median_prof', label:'median profit $/GPU·h'},
      {key:'best_offer',  label:'best offer $'},
      {key:'median_margin', label:'median margin %'},
    ]);
    const rtb = rt.querySelector('tbody'); rtb.innerHTML='';
    for (const r of rl) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="l">${r.model}</td><td>${fmtUsd(r.median_prof)}</td>
                      <td>${fmtUsd(r.best_offer)}</td><td>${isNaN(r.median_margin)?'—':r.median_margin.toFixed(1)+'%'}</td>`;
      rtb.appendChild(tr);
    }
  }

  // ─── suggested token prices per class (only when a specific model picked) ───
  if (!allMode && !cmpMode) {
    const mdl = selModel;
    const pub = P.PUBLIC_PRICE_LIST[mdl];
    const suggLines = [];
    const byGpu = {};
    for (const r of d) {
      if (r.throughput_case !== 'best') continue;
      if (!(r.gpu_class in byGpu) || r.profit_ph > byGpu[r.gpu_class].profit_ph) byGpu[r.gpu_class] = r;
    }
    for (const [g, best] of Object.entries(byGpu)) {
      const hourlyCost = best.eff_cost_ph;
      const { inA, outA } = anchorsFor(mdl, isl, osl, kv);
      const hw = P.HW_SCALE[mdl][g] || 0;
      const totalTps = (inA + outA) * hw;
      const wsum = mixFrac.fresh*P.CLASS_WEIGHT.fresh + mixFrac.cached*P.CLASS_WEIGHT.cached + mixFrac.out*P.CLASS_WEIGHT.out;
      const row = { gpu: g.toUpperCase(), offer: String(best.option_id).slice(0,30),
                    cost_h: hourlyCost, tps_total: totalTps };
      for (const cls of ['fresh','cached','out']) {
        const share = (mixFrac[cls]*P.CLASS_WEIGHT[cls]) / wsum;
        const costC = hourlyCost * share;
        let toksH;
        if (cls==='fresh')  toksH = (inA * hw) * (1 - kv/100) * 3600 * UTIL;
        else if (cls==='cached') toksH = (inA * hw) * (kv/100) * 3600 * UTIL;
        else                toksH = (outA * hw) * 3600 * UTIL;
        const be = costC / Math.max(toksH, 1e-9) * 1e6;
        row[`be_${cls}`] = be;
        for (const [tier, gm] of P.SUG_MARGIN_TIERS) row[`p${tier}_${cls}`] = be / (1 - gm);
        row[`pub_${cls}`] = P.PUBLIC_PRICE_LIST[mdl][cls];
      }
      suggLines.push(row);
    }
    suggLines.sort((a,b)=>a.be_fresh - b.be_fresh);
    if (suggLines.length) {
      const blend = mixFrac.fresh*pub.fresh + mixFrac.cached*pub.cached + mixFrac.out*pub.out;
      $('sugg_title').textContent = `Suggested token prices per class — ${mdl} · mix=${mix} · util=${(UTIL*100).toFixed(0)}%`;
      $('sugg_sub').textContent =
        `public list (from §1): fresh=${pub.fresh} · cached=${pub.cached} · out=${pub.out} · blended=${blend.toFixed(3)}/1M  [${pub.ref}]\n` +
        'cost-share weights: fresh=1.0 · cached=0.20 · out=1.0  (heuristic — tune with measured backend split)\n' +
        'columns: be_* = breakeven $/1M   ·   p30/p50/p70_* = price at 30/50/70% GM   ·   pub_* = public list $/1M';
      const cols = [
        {key:'gpu', label:'GPU', align:'l'},
        {key:'offer', label:'offer', align:'l'},
        {key:'cost_h', label:'cost $/h', fmt:v=>fmtUsd(v,2)},
        {key:'tps_total', label:'t/s', fmt:v=>Math.round(v).toLocaleString()},
      ];
      for (const cls of ['fresh','cached','out']) {
        for (const k of ['be','p30','p50','p70','pub']) {
          cols.push({key:`${k}_${cls}`, label:`${k}_${cls}`, fmt: v=>fmtUsd(v, Math.abs(v)<1?4:3),
                     cls: k==='be' ? 'be' : ''});
        }
      }
      const st = $('sugg_tbl');
      st.innerHTML = '<thead><tr>' + cols.map(c => `<th class="${c.align==='l'?'l':''}">${c.label}</th>`).join('') + '</tr></thead><tbody>' +
        suggLines.map(r => '<tr>' + cols.map(c => {
          const v = r[c.key];
          const clsAttr = c.cls ? ` class="${c.cls}"` : (c.align==='l' ? ' class="l"' : '');
          return `<td${clsAttr}>${c.fmt ? c.fmt(v) : v}</td>`;
        }).join('') + '</tr>').join('') + '</tbody>';
    } else {
      $('sugg_block').style.display = 'none';
    }
  }
}

for (const id of ['w_model','w_price','w_gpu','w_work','w_util']) {
  $(id).addEventListener('input', render);
}
render();
</script>
</body></html>
"""

html = HTML.replace('__PAYLOAD__', json.dumps(PAYLOAD, separators=(',', ':'), default=str))
with open(OUT, 'w') as f: f.write(html)
print(f'wrote {OUT}  ({len(html)/1024:.1f} KB, {len(PAYLOAD["GRID"])} grid rows)')
