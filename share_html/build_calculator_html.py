#!/usr/bin/env python3 -I
"""Build share_html/GPU-LLM-Calculator.html — a self-contained, double-clickable
mirror of notebook §1 (live calculator § 'cell 5' / c5_run).

Data payload: grid_full options (118 rows, ~19KB JSON) + the pricing/anchor/
HW/KV-gain constants copied verbatim from the notebook cell.
Logic:        same formulas ported 1:1 to JS and unit-checked against
              tests/test_cells.json by build-time asserts (see bottom).
"""

import json, os, sys, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # …/v2
# grid_full_v2.csv lives in v2/grid/ (the authoritative copy for the workbook);
# the colab_upload zips carry a snapshot of it.
_DATA_CANDIDATES = [os.path.join(ROOT, 'grid'),
                    os.path.join(ROOT, 'colab_upload', 'GPU-LLM-v2-Analytics-Colab 6'),
                    os.path.join(ROOT, 'colab_upload'),
                    os.path.join(ROOT, 'data')]
def _find(name):
    for d in _DATA_CANDIDATES:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)
OUT  = os.path.join(HERE, 'GPU-LLM-Calculator.html')

# ─── data payload ────────────────────────────────────────────────────────────
import pandas as pd
grid = pd.read_csv(_find('grid_full_v2.csv'))
opts = (grid[(grid.mix=='agentic') & (grid.throughput_case=='best')]
        [['option_id','gpu_class','rental_term','listed_rate','eff_cost_ph','price_src']]
        .drop_duplicates()
        .to_dict(orient='records'))
for r in opts:
    r['listed_rate']  = float(r['listed_rate'])
    r['eff_cost_ph']  = float(r['eff_cost_ph'])

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
    "MODEL_LABELS": {"glm-5.3-flash":"GLM-5.3-Flash (measured)",
                     "kimi-k3":"Kimi-K3 (public anchor)",
                     "deepseek-v4.1-flash":"DeepSeek-V4.1-Flash",
                     "hy4-preview":"Tencent Hy4-preview",
                     "mimo-v2.6-flash":"Xiaomi MiMo-V2.6-Flash"},
    "GPU_LABELS": ["gb300","b300","mi355x","b200","gb200","h200","mi325x","h100"],
    "OPTIONS": opts,
}

# ─── build-time self-check: port the JS maths back to Python and pin the four
# regression cases from tests/test_cells.json against it. If this drifts, fail.
def _kv_gain_at(kv, osl, strength=1.0):
    pts = {(60,128):1.00,(60,256):1.00,(60,512):1.00,(60,1024):1.00,
           (90,128):2.40,(90,256):1.76,(90,512):0.87,(90,1024):0.51}
    kvs  = sorted({p[0] for p in pts});  osls = sorted({p[1] for p in pts})
    kv_c = max(kvs[0], min(kv, kvs[-1])); osl_c = max(osls[0], min(osl, osls[-1]))
    kv_lo = max(k for k in kvs if k <= kv_c); kv_hi = min(k for k in kvs if k >= kv_c)
    osl_lo= max(o for o in osls if o <= osl_c); osl_hi= min(o for o in osls if o >= osl_c)
    f11=pts[(kv_lo,osl_lo)]; f12=pts[(kv_lo,osl_hi)]
    f21=pts[(kv_hi,osl_lo)]; f22=pts[(kv_hi,osl_hi)]
    tx = 0 if kv_hi==kv_lo   else (kv_c-kv_lo)/(kv_hi-kv_lo)
    ty = 0 if osl_hi==osl_lo else (osl_c-osl_lo)/(osl_hi-osl_lo)
    raw = f11*(1-tx)*(1-ty) + f21*tx*(1-ty) + f12*(1-tx)*ty + f22*tx*ty
    return 1.0 + (raw-1.0) * strength

def _rev_h(in_v, out_v, k, P):
    return (in_v*(1-k)*P['pin'] + in_v*k*P['pca'] + out_v*P['pou']) * 3600/1e6

def _anchors_for(model, isl, osl, kv, strength=1.0):
    if model == "glm-5.3-flash":
        gates = PAYLOAD['GATES'][str(isl if isl in (13000,25000) else 25000)]
        kvs = sorted(int(k) for k in gates.keys())
        kv_use = kvs[-1] if kv >= kvs[-1] else (kvs[0] if kv <= kvs[0] else max(k for k in kvs if k <= kv))
        osl_tbl = gates[str(kv_use)]
        osls = sorted(int(o) for o in osl_tbl.keys())
        o_anchor = max(o for o in osls if o <= min(osl, osls[-1]))
        it, ot = osl_tbl[str(o_anchor)]
        return it, ot, 1.0
    a = PAYLOAD['ANCHOR'][model]
    prior = PAYLOAD['KV_GAIN_MODEL_PRIOR'][model]
    gain = _kv_gain_at(kv, osl, strength * prior)
    return a['in_tps']*gain, a['out_tps']*gain, gain

CASES = [  # (model, isl, osl, kv, gpu_class, expected rev_h, abs_tol) — from tests/test_cells.json (refreshed 2026-11-10)
    ("glm-5.3-flash", 25000, 512, 60, "gb300",  7.826,  1e-3),
    ("glm-5.3-flash", 25000, 128, 90, "gb300",  9.481,  1e-3),
    ("kimi-k3",       25000, 512, 60, "b300",  66.726,  1e-3),
    ("kimi-k3",       25000, 128, 90, "b300",  85.551,  1e-2),
]
for m, isl, osl, kv, g, exp, tol in CASES:
    it, ot, _ = _anchors_for(m, isl, osl, kv)
    hw  = PAYLOAD['HW_SCALE'][m][g]
    P   = PAYLOAD['PRICES'][m]
    rev = _rev_h(it*hw, ot*hw, kv/100., P)
    if abs(rev - exp) > tol:
        print(f'SELF-CHECK FAILED {m}/{g}: expected {exp} got {rev}', file=sys.stderr)
        sys.exit(1)
print(f'build self-check: {len(CASES)} pinned cases pass')

# ─── HTML / JS (calculator logic ported 1:1) ─────────────────────────────────
HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GPU Hosting Calculator</title>
<style>
  :root {
    --ink:#0f172a; --ink-2:#475569; --ink-3:#64748b;
    --line:#e2e8f0; --surface:#ffffff; --surface-2:#f8fafc;
    --accent:#0ea5e9; --good:#059669; --warn:#d97706; --bad:#dc2626;
  }
  * { box-sizing:border-box }
  html,body { margin:0; padding:0; background:#f1f5f9; color:var(--ink);
              font:14px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:1240px; margin:24px auto; padding:0 20px 40px; }
  h1 { font-size:17px; margin:0 0 4px; font-weight:700; letter-spacing:-0.01em; }
  .sub { color:var(--ink-3); font-size:12px; margin-bottom:18px; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin-bottom:14px; box-shadow:0 1px 2px rgba(15,23,42,.04); }
  .row { display:flex; flex-wrap:wrap; gap:10px 14px; align-items:flex-end; }
  .fld { display:flex; flex-direction:column; gap:3px; min-width:118px; }
  .fld > label { font-size:10.5px; font-weight:600; color:var(--ink-3); text-transform:uppercase; letter-spacing:.06em; }
  select, input[type=number], input[type=text] {
    font:inherit; padding:5px 8px; border:1px solid var(--line); border-radius:6px;
    background:var(--surface); color:var(--ink); }
  select:focus, input:focus { outline:2px solid var(--accent); outline-offset:1px; border-color:var(--accent); }
  input[type=range] { accent-color:var(--accent); padding:0; }
  .w-num { width:92px; }
  .hdr { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
         font-size:11.5px; color:var(--ink-2); white-space:pre-wrap; margin:0 0 10px; }
  .hdr strong { color:var(--ink); }
  .tblscroll { max-height:520px; overflow:auto; border:1px solid var(--line); border-radius:8px; }
  table { border-collapse:collapse; width:100%; font-size:12px; }
  thead th { position:sticky; top:0; background:var(--surface-2); color:var(--ink-3);
             font-size:10.5px; font-weight:600; text-transform:uppercase; letter-spacing:.05em;
             padding:7px 10px; text-align:right; border-bottom:1px solid var(--line); cursor:pointer; user-select:none; }
  thead th:hover { color:var(--ink); }
  tbody td { padding:5px 10px; text-align:right; border-top:1px solid #f1f5f9;
             font-variant-numeric:tabular-nums; }
  tbody tr:first-child td { border-top:none }
  tbody tr:hover { background:#f1f9ff }
  td.l, th.l { text-align:left }
  .pos { color:var(--good); font-weight:600 }
  .neg { color:var(--bad);  font-weight:600 }
  .psz { font-size:10px; padding:1px 6px; border-radius:4px; font-weight:600; }
  .psz.my  { background:#fff4d6; color:#92400e }
  .psz.pub { background:#e8f1fc; color:#1e3a8a }
  .foot { color:var(--ink-3); font-size:11px; margin-top:8px; }
  .nn { color:var(--ink-3) }   /* N/A cell */
</style>
</head>
<body>
<div class="wrap">
  <h1>GPU Hosting Calculator</h1>
  <div class="sub">§1 mirror from <code>GPU-LLM-v2-Analytics.ipynb</code> — revenue &amp; break-even for 5 models × your workload, against the live price grid. Values update on input.</div>

  <div class="card">
    <div class="row">
      <div class="fld"><label>Model</label>
        <select id="w_model"></select></div>
      <div class="fld"><label>My workload (ISL)</label>
        <select id="w_isl">
          <option value="25000" selected>ISL 25k</option>
          <option value="13000">ISL 13k</option>
        </select></div>
      <div class="fld"><label>OSL tokens</label>
        <input class="w-num" type="number" id="w_osl" min="128" max="4096" step="1" value="512"></div>
      <div class="fld"><label>KV hit %</label>
        <input class="w-num" type="number" id="w_kv" min="0" max="100" step="1" value="60"></div>
    </div>
    <div class="row" style="margin-top:10px">
      <div class="fld"><label>Fresh-in $/1M</label>
        <input class="w-num" type="number" id="w_pin" step="0.01" value="0.15"></div>
      <div class="fld"><label>Cached-in $/1M</label>
        <input class="w-num" type="number" id="w_pca" step="0.001" value="0.03"></div>
      <div class="fld"><label>Out $/1M</label>
        <input class="w-num" type="number" id="w_pou" step="0.01" value="0.50"></div>
      <div class="fld"><label>Hardware</label>
        <select id="w_gpu"></select></div>
      <div class="fld"><label>Price source</label>
        <select id="w_price">
          <option value="both" selected>both</option>
          <option value="my_quotes">my offers</option>
          <option value="public_market">public market</option>
        </select></div>
    </div>
    <div class="row" style="margin-top:10px">
      <div class="fld"><label>GPUs (nodes)</label>
        <input class="w-num" type="number" id="w_fleet" min="1" step="1" value="16"></div>
      <div class="fld"><label>Window (days)</label>
        <input class="w-num" type="number" id="w_horizon" min="1" step="1" value="7"></div>
      <div class="fld" style="min-width:190px"><label>GPU utilisation % · <span id="v_util">100</span></label>
        <input type="range" id="w_util" min="10" max="100" step="5" value="100"></div>
    </div>
  </div>

  <div class="card">
    <div class="hdr" id="hd"></div>
    <div class="tblscroll">
      <table id="tbl">
        <thead><tr>
          <th class="l" data-k="option_id">offer</th>
          <th class="l" data-k="gpu_class">gpu</th>
          <th class="l" data-k="price_src">src</th>
          <th data-k="profit_ph">profit $/GPU·h</th>
          <th data-k="margin_pct">margin %</th>
          <th data-k="revenue_ph">revenue $/h</th>
          <th data-k="profit_total">profit total</th>
          <th data-k="cost_total">cost total</th>
          <th data-k="revenue_total">revenue total</th>
          <th data-k="be_lower">break-even util</th>
          <th data-k="listed_rate">list $/h</th>
          <th data-k="hw_scale">hw ×</th>
          <th data-k="fresh_in_tps">fresh in t/s</th>
          <th data-k="cached_in_tps">cached in t/s</th>
          <th data-k="out_tps">out t/s</th>
        </tr></thead>
        <tbody id="tb"></tbody>
      </table>
    </div>
    <div class="foot" id="ft"></div>
  </div>
</div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
'use strict';
const P = JSON.parse(document.getElementById('payload').textContent);

// ── maths, ported 1:1 from notebook cell 5 ──────────────────────────────────
function kvGainAt(kv, osl, strength=1.0) {
  const pts = P.KV_GAIN_PTS;
  const kvs  = [...new Set(Object.keys(pts).map(k => +k.split(',')[0]))].sort((a,b)=>a-b);
  const osls = [...new Set(Object.keys(pts).map(k => +k.split(',')[1]))].sort((a,b)=>a-b);
  const kvC  = Math.max(kvs[0],  Math.min(kv,  kvs[kvs.length-1]));
  const oslC = Math.max(osls[0], Math.min(osl, osls[osls.length-1]));
  const kvLo = Math.max(...kvs.filter(k => k <= kvC));
  const kvHi = Math.min(...kvs.filter(k => k >= kvC));
  const oslLo= Math.max(...osls.filter(o => o <= oslC));
  const oslHi= Math.min(...osls.filter(o => o >= oslC));
  const f11 = pts[`${kvLo},${oslLo}`], f12 = pts[`${kvLo},${oslHi}`];
  const f21 = pts[`${kvHi},${oslLo}`], f22 = pts[`${kvHi},${oslHi}`];
  const tx = kvHi  === kvLo  ? 0 : (kvC  - kvLo ) / (kvHi  - kvLo );
  const ty = oslHi === oslLo ? 0 : (oslC - oslLo) / (oslHi - oslLo);
  const raw = f11*(1-tx)*(1-ty) + f21*tx*(1-ty) + f12*(1-tx)*ty + f22*tx*ty;
  return 1.0 + (raw - 1.0) * strength;
}

function anchorsFor(model, isl, osl, kv) {
  if (model === 'glm-5.3-flash') {
    const gates = P.GATES[isl] || P.GATES['25000'];
    const kvs = Object.keys(gates).map(Number).sort((a,b)=>a-b);
    const kvUse = kv >= kvs[kvs.length-1] ? kvs[kvs.length-1]
                : kv <= kvs[0]            ? kvs[0]
                : Math.max(...kvs.filter(k => k <= kv));
    const tbl  = gates[String(kvUse)];
    const osls = Object.keys(tbl).map(Number).sort((a,b)=>a-b);
    const cap  = Math.min(osl, osls[osls.length-1]);
    const anch = Math.max(...osls.filter(o => o <= cap));
    const [it, ot] = tbl[String(anch)];
    return { inA: it, outA: ot, gain: 1.0, note: 'measured' };
  }
  const a = P.ANCHOR[model];
  const prior = P.KV_GAIN_MODEL_PRIOR[model];
  const gain  = kvGainAt(kv, osl, 1.0 * prior);
  return { inA: a.in_tps * gain, outA: a.out_tps * gain, gain,
           note: `public anchor × ${gain.toFixed(2)} KV-gain (model-prior=${prior.toFixed(2)})` };
}

// ── widget wiring ───────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const wModel = $('w_model'), wGpu = $('w_gpu');
for (const [k, lbl] of Object.entries(P.MODEL_LABELS)) {
  const o = document.createElement('option'); o.value = k; o.textContent = lbl;
  wModel.appendChild(o);
}
{
  const o = document.createElement('option'); o.value='__all__'; o.textContent='all GPUs (scaled)';
  wGpu.appendChild(o);
  for (const g of P.GPU_LABELS) {
    const o = document.createElement('option'); o.value=g; o.textContent=g.toUpperCase();
    wGpu.appendChild(o);
  }
}

let lastModel = null;
function syncPrices() {
  const m = wModel.value;
  if (m !== lastModel) {
    lastModel = m;
    const pq = P.PRICES[m];
    $('w_pin').value = pq.pin; $('w_pca').value = pq.pca; $('w_pou').value = pq.pou;
  }
}

let sortKey = 'profit_total', sortDir = -1;
document.querySelectorAll('#tbl thead th').forEach(th => {
  th.addEventListener('click', () => {
    const k = th.dataset.k;
    if (k === sortKey) sortDir = -sortDir; else { sortKey = k; sortDir = -1; }
    render();
  });
});

const fmtUsd = (v, d=0) => (v==null||isNaN(v)) ? '—' : ('$' + Number(v).toLocaleString('en-US',{maximumFractionDigits:d, minimumFractionDigits:d}));
const fmtSignUsd = (v, d=0) => (v==null||isNaN(v)) ? '—' : ((v>=0?'+':'−') + '$' + Math.abs(v).toLocaleString('en-US',{maximumFractionDigits:d, minimumFractionDigits:d}));

function render() {
  syncPrices();
  const MODEL = wModel.value;
  const ISL   = +$('w_isl').value;
  const OSL   = +$('w_osl').value;
  const KV    = +$('w_kv').value;
  const N     = +$('w_fleet').value;
  const DAYS  = +$('w_horizon').value;
  const UTIL  = +$('w_util').value / 100;
  const PRICE = {pin:+$('w_pin').value, pca:+$('w_pca').value, pou:+$('w_pou').value};
  const SRC   = $('w_price').value;
  $('v_util').textContent = Math.round(UTIL*100);

  const hw = P.HW_SCALE[MODEL];
  const sel = wGpu.value;
  const { inA, outA, gain, note } = anchorsFor(MODEL, ISL, OSL, KV);
  const k = KV / 100;
  const revH = (inv, outv) => (inv*(1-k)*PRICE.pin + inv*k*PRICE.pca + outv*PRICE.pou) * 3600/1e6;
  const revB300 = revH(inA, outA);

  const hwLabel = (sel==='__all__')
    ? 'all GPUs (each row scaled by its own hw_scale vs B300)'
    : `only ${sel.toUpperCase()} · t/s ×${(hw[sel]??1).toFixed(3)}`;

  let rows = P.OPTIONS.filter(r => SRC==='both' || r.price_src===SRC);
  if (sel !== '__all__') rows = rows.filter(r => r.gpu_class === sel);
  // de-dupe on (option_id, gpu_class, price_src) — pandas used drop_duplicates
  const seen = new Set();
  rows = rows.filter(r => {
    const key = `${r.option_id}|${r.gpu_class}|${r.price_src}`;
    if (seen.has(key)) return false; seen.add(key); return true;
  });

  const hours = DAYS * 24;
  const out = [];
  for (const r of rows) {
    const scale = (sel==='__all__') ? (hw[r.gpu_class] ?? 1.0) : (hw[sel] ?? 1.0);
    if (scale === 0) continue;                          // model can't run on this GPU
    const revenue_ph = revH(inA * scale, outA * scale);
    if (isNaN(revenue_ph)) continue;
    const profit_ph    = revenue_ph * UTIL - r.eff_cost_ph;
    const margin_pct   = revenue_ph * UTIL ? profit_ph / (revenue_ph * UTIL) * 100 : NaN;
    const be_lower     = r.eff_cost_ph / revenue_ph;
    out.push({
      option_id: r.option_id, gpu_class: r.gpu_class, price_src: r.price_src,
      listed_rate: r.listed_rate, hw_scale: scale,
      revenue_ph, profit_ph, margin_pct, be_lower,
      fresh_in_tps: inA * scale * (1-k),
      cached_in_tps: inA * scale * k,
      out_tps: outA * scale,
      revenue_total: revenue_ph * UTIL * N * hours,
      cost_total:    r.eff_cost_ph * N * hours,
      profit_total:  profit_ph  * N * hours,
    });
  }

  // sort
  out.sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    if (typeof av === 'string') return sortDir * String(av).localeCompare(String(bv));
    return sortDir * ((av ?? -Infinity) - (bv ?? -Infinity));
  });

  // header text
  const official = P.PRICES[MODEL];
  const isOfficial = Math.abs(PRICE.pin-official.pin)<1e-9 &&
                     Math.abs(PRICE.pca-official.pca)<1e-9 &&
                     Math.abs(PRICE.pou-official.pou)<1e-9;
  $('hd').innerHTML =
    `<strong>WORKLOAD</strong>  ${MODEL}  isl=${ISL.toLocaleString()}  osl=${OSL}  KV=${KV}%  ·  KV-gain ${gain.toFixed(2)}   [${note}]\n` +
    `  B300 anchor: in ${inA.toLocaleString('en-US',{maximumFractionDigits:0})} t/s + out ${outA.toLocaleString('en-US',{maximumFractionDigits:1})} t/s = ${(inA+outA).toLocaleString('en-US',{maximumFractionDigits:0})} mixed t/s  (revenue ${fmtUsd(revB300,3)}/GPU·h on B300)\n` +
    `  prices: fresh-in $${PRICE.pin}/1M · cached-in $${PRICE.pca}/1M · out $${PRICE.pou}/1M\n` +
    `    · ${MODEL} rate card: fresh $${official.pin} · cached $${official.pca} · out $${official.pou} $/1M  [${isOfficial?'official':'OVERRIDDEN'}]\n` +
    `  hardware: ${hwLabel}\n` +
    `  fleet: ${N} GPU  ×  window: ${DAYS} days (${Math.round(hours)} h)  ×  utilisation ${(UTIL*100).toFixed(0)}%`;

  // rows
  const tb = $('tb'); tb.innerHTML = '';
  for (const r of out) {
    const tr = document.createElement('tr');
    const cls = r.profit_total >= 0 ? 'pos' : 'neg';
    const psz = r.price_src === 'my_quotes'
      ? '<span class="psz my">my</span>' : '<span class="psz pub">pub</span>';
    tr.innerHTML =
      `<td class="l">${r.option_id}</td>` +
      `<td class="l">${r.gpu_class.toUpperCase()}</td>` +
      `<td class="l">${psz}</td>` +
      `<td class="${cls}">${fmtSignUsd(r.profit_ph,3)}</td>` +
      `<td>${isNaN(r.margin_pct)?'—':r.margin_pct.toFixed(1)+'%'}</td>` +
      `<td>${fmtUsd(r.revenue_ph,3)}</td>` +
      `<td class="${cls}">${fmtSignUsd(r.profit_total,0)}</td>` +
      `<td>${fmtUsd(r.cost_total,0)}</td>` +
      `<td>${fmtUsd(r.revenue_total,0)}</td>` +
      `<td>${(r.be_lower*100).toFixed(1)}%</td>` +
      `<td>${fmtUsd(r.listed_rate,2)}</td>` +
      `<td>${r.hw_scale.toFixed(3)}</td>` +
      `<td>${Math.round(r.fresh_in_tps).toLocaleString()}</td>` +
      `<td>${Math.round(r.cached_in_tps).toLocaleString()}</td>` +
      `<td>${r.out_tps.toFixed(1)}</td>`;
    tb.appendChild(tr);
  }
  $('ft').textContent = out.length
    ? `${out.length} offers · sorted by ${document.querySelector(`th[data-k="${sortKey}"]`).textContent} (${sortDir===-1?'desc':'asc'}) · click any column to re-sort`
    : 'no rows for this combination';
}

['w_model','w_isl','w_osl','w_kv','w_pin','w_pca','w_pou','w_gpu','w_price','w_fleet','w_horizon','w_util']
  .forEach(id => $(id).addEventListener('input', render));
render();
</script>
</body>
</html>
"""

html = HTML.replace('__PAYLOAD__', json.dumps(PAYLOAD, separators=(',', ':')))
os.makedirs(HERE, exist_ok=True)
with open(OUT, 'w') as f:
    f.write(html)
print(f'wrote {OUT}  ({len(html)/1024:.1f} KB, {len(opts)} offers embedded)')
