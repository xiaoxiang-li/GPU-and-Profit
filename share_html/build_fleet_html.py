#!/usr/bin/env python3 -I
"""Build share_html/GPU-LLM-Fleet.html — self-contained mirror of the §0b
Fleet & Cost panel. Reads fleet_gpu_rentals.csv, embeds a snapshot as JSON,
and renders KPIs + per-host occupancy waffle + money-in/out + expiry table +
detail table — all in JS, no Python needed for the viewer."""

import json, os, sys
import pandas as pd
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT  = os.path.join(HERE, 'GPU-LLM-Fleet.html')

CSV = None
for cand in [os.path.join(ROOT, 'colab_upload', 'GPU-LLM-v2-Analytics-Colab 6',
                          'fleet_gpu_rentals.csv'),
             os.path.join(ROOT, 'data', 'fleet_gpu_rentals.csv')]:
    if os.path.exists(cand):
        CSV = cand; break
if CSV is None:
    print('fleet_gpu_rentals.csv not found', file=sys.stderr); sys.exit(1)

df = pd.read_csv(CSV, encoding='utf-8-sig')
df = df[pd.to_numeric(df['GPU Count'], errors='coerce').notna()].copy()
df['GPU Count']      = df['GPU Count'].astype(int)
df['Monthly Cost']   = pd.to_numeric(df['Monthly Cost ($/month)'].astype(str).str.replace(',',''), errors='coerce')
df['Unit Price']     = pd.to_numeric(df['Unit Price ($/GPU/h)'], errors='coerce')
df['End Date']       = pd.to_datetime(df['End Date'], errors='coerce')
df['Customer']       = df['Customer'].astype(str).str.strip().replace('-','')

rows = []
INTERNAL_IPS = {}
for _, r in df.iterrows():
    rows.append({
        'resource':   str(r['Resource']),
        'vendor':     str(r['Vendor']),
        'gpu_model':  str(r['GPU Model']),
        'scope':      str(r['Allocation Scope']),
        'customer':   str(r['Customer']) if r['Customer'] != 'nan' else '',
        'purpose':    str(r.get('Purpose','') or ''),
        'end_date':   r['End Date'].strftime('%Y-%m-%d') if pd.notna(r['End Date']) else None,
        'gpu_count':  int(r['GPU Count']),
        'unit_price': float(r['Unit Price']) if pd.notna(r['Unit Price']) else None,
        'monthly_cost': float(r['Monthly Cost']) if pd.notna(r['Monthly Cost']) else None,
    })

# initial occupancy for internal rows, mirrors notebook FLEET_DEFAULT_OCCUPANCY
DEFAULT_OCC = {
    'Reactor (Alibaba)  B300 - 47.250.177.205': 8,
    'Reactor (Alibaba) B300 - 47.250.166.190':  8,
    'Manifold B300 - 63.97.218.1':              8,
    'Manifold B300 - 63.97.218.8':              8,
    'Vessl H100':                               0,
}

PAYLOAD = {
    'rows': rows,
    'default_occupancy': DEFAULT_OCC,
    'as_of': datetime.now().strftime('%Y-%m-%d'),
}

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fleet &amp; Cost — GPU LLM</title>
<style>
  :root { --ink:#0f172a; --ink-2:#475569; --ink-3:#64748b; --line:#e2e8f0;
          --surface:#fff; --surface-2:#f8fafc; --good:#059669; --warn:#d97706; --bad:#dc2626;
          --accent:#0ea5e9; }
  * { box-sizing:border-box }
  body { margin:0; padding:0; background:#f1f5f9; color:var(--ink);
         font:14px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:1280px; margin:24px auto; padding:0 20px 40px; }
  h1 { font-size:17px; margin:0 0 4px; font-weight:700; }
  .sub { color:var(--ink-3); font-size:12px; margin-bottom:18px; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin-bottom:14px; box-shadow:0 1px 2px rgba(15,23,42,.04); }
  .kpis { display:flex; flex-wrap:wrap; gap:10px; margin:0 0 14px; }
  .kpi { flex:1; min-width:170px; padding:12px 14px; border-radius:8px;
         background:var(--surface-2); border:1px solid var(--line); }
  .kpi .l { font-size:10px; font-weight:600; color:var(--ink-3); text-transform:uppercase; letter-spacing:.08em; }
  .kpi .v { font-size:20px; font-weight:700; color:var(--ink); margin-top:3px; }
  .kpi .s { font-size:11px; color:var(--ink-3); margin-top:2px; }
  .pos { color:var(--good) } .neg { color:var(--bad) }

  table { border-collapse:collapse; width:100%; font-size:12px; }
  thead th { background:var(--surface-2); color:var(--ink-3); font-size:10.5px;
             font-weight:600; text-transform:uppercase; letter-spacing:.05em;
             padding:7px 10px; text-align:right; border-bottom:1px solid var(--line); }
  tbody td { padding:5px 10px; text-align:right; border-top:1px solid #f1f5f9;
             font-variant-numeric:tabular-nums; }
  td.l, th.l { text-align:left }
  td.ctr, th.ctr { text-align:center }
  tr.customer td { background:#ecfdf5 }
  tr.zero-occ td  { background:#fef2f2 }
  .occ-cell { font-variant-numeric:tabular-nums; font-weight:600; }
  .tag { display:inline-block; padding:1px 6px; border-radius:4px; font-size:10.5px; font-weight:600; }
  .tag.g { background:#d1fae5; color:#065f46 }
  .tag.a { background:#fef3c7; color:#92400e }
  .tag.r { background:#fee2e2; color:#991b1b }
  .tag.x { background:#7f1d1d; color:#fff }
  .tag.n { background:#f1f5f9; color:#475569 }
  input[type=number] { width:74px; font:inherit; padding:3px 6px;
                       border:1px solid var(--line); border-radius:6px; background:#fff; }
  .controls { display:flex; flex-wrap:wrap; gap:14px 24px; padding:10px 14px; background:var(--surface-2);
              border:1px solid var(--line); border-radius:8px; margin-bottom:14px; font-size:12px; }
  .controls .grp { display:flex; flex-direction:column; gap:3px; }
  .controls .lbl { font-size:10px; font-weight:600; color:var(--ink-3); text-transform:uppercase; letter-spacing:.06em; }
  .controls input[type=number] { width:120px }
  .ctl-row { display:flex; align-items:center; gap:8px; padding:3px 0; }
  .ctl-row input[type=range] { width:170px; accent-color:var(--accent) }
  .ctl-row .val { min-width:36px; text-align:right; font-variant-numeric:tabular-nums; color:var(--ink-2); }
  .ctl-row .nm  { width:300px; color:var(--ink-2); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  h2 { font-size:13px; font-weight:700; margin:0 0 8px; color:var(--ink); }
  .note { color:var(--ink-3); font-size:11px; margin-top:8px; }
</style></head>
<body><div class="wrap">
  <h1>Fleet &amp; Cost</h1>
  <div class="sub">Section 0b mirror. Snapshot of <code>fleet_gpu_rentals.csv</code> as of <span id="asof"></span>. Drag an occupancy slider or type a customer revenue to see every number below update.</div>

  <div class="kpis" id="kpis"></div>

  <div class="card">
    <h2>Inputs</h2>
    <div class="controls">
      <div class="grp" style="flex:1; min-width:340px">
        <div class="lbl">Internal occupancy · GPUs in use</div>
        <div id="occInputs"></div>
      </div>
      <div class="grp" style="flex:1; min-width:280px">
        <div class="lbl">Customer revenue ($/month)</div>
        <div id="revInputs"></div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Waterfall — money in vs money out vs net</h2>
    <div style="max-width:700px; margin:0 auto" id="pnl"></div>
  </div>

  <div class="card">
    <h2>Per-host occupancy</h2>
    <div class="tblscroll"><table id="occTbl">
      <thead><tr>
        <th class="l">host</th><th class="ctr">GPU ■ used / □ idle</th>
        <th class="ctr">used / total</th><th class="ctr">occ %</th>
        <th>cost $/mo</th><th>idle $/mo</th><th class="l">expires · days</th>
      </tr></thead>
      <tbody id="occBody"></tbody>
    </table></div>
  </div>

  <div class="card">
    <h2>Contract expiry</h2>
    <div class="tblscroll"><table id="expTbl">
      <thead><tr>
        <th class="l">host</th><th class="ctr">scope</th><th class="ctr">GPU</th><th class="ctr">count</th>
        <th>$/mo freed</th><th class="ctr">end date</th><th class="ctr">days left</th>
      </tr></thead>
      <tbody id="expBody"></tbody>
    </table></div>
  </div>

  <div class="card">
    <h2>Cost by vendor × scope</h2>
    <div class="tblscroll"><table id="costTbl">
      <thead><tr>
        <th class="l">GPU model</th><th class="l">vendor</th>
        <th>internal $/mo</th><th>customer $/mo</th><th>total $/mo</th>
      </tr></thead>
      <tbody id="costBody"></tbody>
    </table></div>
  </div>

  <div class="card">
    <h2>Detail</h2>
    <div class="tblscroll"><table id="detTbl">
      <thead><tr>
        <th class="l">resource</th><th class="l">vendor</th><th class="ctr">GPU</th><th class="ctr">scope</th>
        <th class="l">customer</th><th class="ctr">count</th><th class="ctr">in use</th><th class="ctr">occ %</th>
        <th>unit $/h</th><th>monthly $</th><th>revenue $</th><th>net $</th><th class="l">end date</th><th class="l">purpose</th>
      </tr></thead>
      <tbody id="detBody"></tbody>
    </table></div>
  </div>
</div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
'use strict';
const P = JSON.parse(document.getElementById('payload').textContent);
document.getElementById('asof').textContent = P.as_of;

// internal hosts (unique by resource, scope=Internal)
const hosts = P.rows.filter(r => r.scope === 'Internal');
// initial occupancy map: explicit default else full count
function initOcc(res, cnt) {
  for (const k of Object.keys(P.default_occupancy)) {
    if (res.trim().startsWith(k.trim().slice(0, 30))) return P.default_occupancy[k];
  }
  return cnt;
}
const state = {
  occ:      Object.fromEntries(hosts.map(r => [r.resource, initOcc(r.resource, r.gpu_count)])),
  revenue:  {},   // customer name → $/mo
};

// customers (dedupe, drop empty/nan)
const customers = [...new Set(P.rows.map(r => r.customer).filter(c => c && c !== 'nan'))].sort();
customers.push('Other');
for (const c of customers) state.revenue[c] = 0;

// build inputs
const occDiv = document.getElementById('occInputs');
for (const h of hosts) {
  const row = document.createElement('div'); row.className = 'ctl-row';
  row.innerHTML = `<span class="nm" title="${h.resource}">${h.resource}</span>` +
                  `<input type="range" min="0" max="${h.gpu_count}" step="1" value="${state.occ[h.resource]}">` +
                  `<span class="val">${state.occ[h.resource]}/${h.gpu_count}</span>`;
  const r = row.querySelector('input'), v = row.querySelector('.val');
  r.addEventListener('input', () => {
    state.occ[h.resource] = +r.value;
    v.textContent = `${r.value}/${h.gpu_count}`;
    render();
  });
  occDiv.appendChild(row);
}
const revDiv = document.getElementById('revInputs');
for (const c of customers) {
  const row = document.createElement('div'); row.className = 'ctl-row';
  row.innerHTML = `<span class="nm" style="width:140px">${c}</span>` +
                  `<input type="number" min="0" step="1000" value="0" style="width:120px">` +
                  `<span class="val" style="min-width:60px">$/mo</span>`;
  const inp = row.querySelector('input');
  inp.addEventListener('input', () => { state.revenue[c] = +inp.value || 0; render(); });
  revDiv.appendChild(row);
}

const $ = id => document.getElementById(id);
const fmtUsd = (v, d=0) => (v==null||isNaN(v)) ? '—' :
  ('$' + Number(v).toLocaleString('en-US',{maximumFractionDigits:d, minimumFractionDigits:d}));
const today = new Date(P.as_of + 'T00:00:00');

function compute() {
  const out = P.rows.map(r => {
    const internal = r.scope === 'Internal';
    const used     = internal ? Math.min(state.occ[r.resource] ?? r.gpu_count, r.gpu_count) : r.gpu_count;
    const occ      = r.gpu_count > 0 ? 100 * used / r.gpu_count : NaN;
    const revenue  = state.revenue[r.customer] || 0;
    return {...r, gpus_in_use: used, occ_pct: occ, cust_rev: revenue,
            net: revenue - (r.monthly_cost || 0)};
  });
  const ints = out.filter(r => r.scope === 'Internal');
  const cuts = out.filter(r => r.scope === 'Customer');
  const agg = {
    total_gpus:       out.reduce((a,r)=>a+r.gpu_count,0),
    internal_gpus:    ints.reduce((a,r)=>a+r.gpu_count,0),
    customer_gpus:    cuts.reduce((a,r)=>a+r.gpu_count,0),
    total_cost:       out.reduce((a,r)=>a+(r.monthly_cost||0),0),
    internal_cost:    ints.reduce((a,r)=>a+(r.monthly_cost||0),0),
    customer_cost:    cuts.reduce((a,r)=>a+(r.monthly_cost||0),0),
    internal_in_use:  ints.reduce((a,r)=>a+r.gpus_in_use,0),
    customer_revenue: out.reduce((a,r)=>a+r.cust_rev,0),
  };
  agg.net = agg.customer_revenue - agg.total_cost;
  agg.internal_occupancy = agg.internal_gpus ? 100*agg.internal_in_use/agg.internal_gpus : NaN;
  agg.known_revenue      = agg.customer_revenue > 0;
  return {rows: out, totals: agg};
}

function band(pct) { return pct >= 75 ? 'g' : pct >= 40 ? 'a' : pct > 0 ? 'r' : 'n'; }

function render() {
  const {rows, totals} = compute();

  // KPIs
  const cov = totals.known_revenue && totals.internal_cost > 0
    ? `${Math.round(totals.customer_revenue / totals.internal_cost * 100)}% of Internal cost`
    : 'no revenue data yet';
  $('kpis').innerHTML = `
    <div class="kpi"><div class="l">Total GPUs</div><div class="v">${totals.total_gpus}</div>
      <div class="s">Internal ${totals.internal_gpus} · Customer ${totals.customer_gpus}</div></div>
    <div class="kpi"><div class="l">Total monthly cost</div><div class="v">${fmtUsd(totals.total_cost)}</div>
      <div class="s">Internal ${fmtUsd(totals.internal_cost)} · Customer ${fmtUsd(totals.customer_cost)}</div></div>
    <div class="kpi"><div class="l">Customer revenue</div><div class="v">${totals.known_revenue?fmtUsd(totals.customer_revenue):'—'}</div>
      <div class="s">${cov}</div></div>
    <div class="kpi"><div class="l">Net P&amp;L / month</div><div class="v ${totals.net>=0?'pos':'neg'}">${((totals.net>=0?'+':'-'))+fmtUsd(Math.abs(totals.net)).slice(0)}</div>
      <div class="s">revenue − all fleet cost</div></div>
    <div class="kpi"><div class="l">Internal occupancy</div><div class="v">${totals.internal_occupancy.toFixed(0)}%</div>
      <div class="s">${totals.internal_in_use}/${totals.internal_gpus} GPUs in use</div></div>`;

  // occupancy table
  const occBody = $('occBody'); occBody.innerHTML = '';
  const ints = rows.filter(r => r.scope==='Internal')
                   .sort((a,b) => (b.monthly_cost||0) - (a.monthly_cost||0));
  const maxN = Math.max(...ints.map(r => r.gpu_count), 1);
  for (const r of ints) {
    const tr = document.createElement('tr');
    const used = r.gpus_in_use, n = r.gpu_count;
    const pct  = r.occ_pct;
    const sqs = Array.from({length: n}, (_, i) =>
      `<span style="display:inline-block; width:14px; height:18px; margin:0 2px; border-radius:2px;
                    background:${i < used ? (pct>=75?'#059669':pct>=40?'#d97706':'#dc2626') : '#f1f5f9'};
                    border:1px solid ${i < used ? 'transparent' : '#cbd5e1'}"></span>`).join('');
    const idle = (r.monthly_cost||0) * (1 - pct/100);
    const endD = r.end_date ? new Date(r.end_date + 'T00:00:00') : null;
    const days = endD ? Math.round((endD - today) / 86400000) : null;
    tr.className = used === 0 ? 'zero-occ' : '';
    tr.innerHTML = `<td class="l">${r.resource}</td>
      <td class="ctr">${sqs}</td>
      <td class="ctr"><strong>${used}/${n}</strong></td>
      <td class="ctr occ-cell"><span class="tag ${band(pct)}">${pct.toFixed(0)}%</span></td>
      <td>${fmtUsd(r.monthly_cost)}</td>
      <td class="${idle > 5000 ? 'neg' : ''}">${idle > 0 ? fmtUsd(idle) : '—'}</td>
      <td class="l">${r.end_date || '—'} · ${days===null?'—':days+'d'}</td>`;
    occBody.appendChild(tr);
  }

  // expiry table
  const expBody = $('expBody'); expBody.innerHTML = '';
  const exp = rows.filter(r => r.end_date).slice()
                  .sort((a,b) => a.end_date.localeCompare(b.end_date));
  for (const r of exp) {
    const endD = new Date(r.end_date + 'T00:00:00');
    const days = Math.round((endD - today) / 86400000);
    const tr = document.createElement('tr');
    let badge, cls='';
    if (days < 0)      { badge = `<span class="tag x">ended ${-days} d ago</span>`; cls='customer-zero'; }
    else if (days<=90) { badge = `<span class="tag r">${days} d</span>`; }
    else if (days<=180){ badge = `<span class="tag r">${days} d</span>`; }
    else if (days<=365){ badge = `<span class="tag a">${days} d</span>`; }
    else               { badge = `<span class="tag n">${days} d</span>`; }
    if (days <= 180) tr.style.background = '#fef2f2';
    tr.innerHTML = `<td class="l">${r.resource}</td><td class="ctr">${r.scope}</td>
      <td class="ctr">${r.gpu_model}</td><td class="ctr">${r.gpu_count}</td>
      <td>${fmtUsd(r.monthly_cost)}</td><td class="ctr">${r.end_date}</td>
      <td class="ctr">${badge}</td>`;
    expBody.appendChild(tr);
  }

  // cost-by-vendor × scope
  const costBody = $('costBody'); costBody.innerHTML = '';
  const map = {};
  for (const r of rows) {
    const k = `${r.gpu_model}|${r.vendor}`;
    map[k] = map[k] || {gpu:r.gpu_model, vendor:r.vendor, Internal:0, Customer:0};
    if (r.scope === 'Internal') map[k].Internal += r.monthly_cost || 0;
    else if (r.scope === 'Customer') map[k].Customer += r.monthly_cost || 0;
  }
  for (const k of Object.values(map).sort((a,b) => (b.Internal+b.Customer) - (a.Internal+a.Customer))) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="l">${k.gpu}</td><td class="l">${k.vendor}</td>
      <td>${k.Internal?fmtUsd(k.Internal):'—'}</td>
      <td>${k.Customer?fmtUsd(k.Customer):'—'}</td>
      <td><strong>${fmtUsd(k.Internal + k.Customer)}</strong></td>`;
    costBody.appendChild(tr);
  }

  // detail table
  const detBody = $('detBody'); detBody.innerHTML = '';
  for (const r of rows) {
    const tr = document.createElement('tr');
    if (r.scope === 'Customer') tr.className = 'customer';
    else if (r.gpus_in_use === 0 && r.scope === 'Internal') tr.className = 'zero-occ';
    const netCls = r.cust_rev - (r.monthly_cost||0) >= 0 ? 'pos' : 'neg';
    tr.innerHTML = `<td class="l">${r.resource}</td><td class="l">${r.vendor}</td>
      <td class="ctr">${r.gpu_model}</td><td class="ctr">${r.scope}</td>
      <td class="l">${r.customer || '—'}</td><td class="ctr">${r.gpu_count}</td>
      <td class="ctr">${r.gpus_in_use}</td><td class="ctr">${isNaN(r.occ_pct)?'—':r.occ_pct.toFixed(0)+'%'}</td>
      <td>${r.unit_price===null?'—':fmtUsd(r.unit_price,2)}</td><td>${fmtUsd(r.monthly_cost)}</td>
      <td>${r.cust_rev?fmtUsd(r.cust_rev):'—'}</td>
      <td class="${netCls}">${((r.cust_rev - (r.monthly_cost||0) >= 0?'+':'-'))+fmtUsd(Math.abs(r.cust_rev - (r.monthly_cost||0))).slice(0)}</td>
      <td class="l">${r.end_date || '—'}</td><td class="l">${r.purpose || ''}</td>`;
    detBody.appendChild(tr);
  }

  // P&L — render as inline SVG, three bars
  const rev   = totals.known_revenue ? totals.customer_revenue : 0;
  const costT = totals.total_cost;
  const net   = totals.net;
  const top   = Math.max(rev, costT, Math.abs(net), 1);
  const H = 240, W = 620, pad = 36, midY = H/2 + 10;
  const y = v => midY - (v / top) * (H/2 - pad);
  const barW = 110;
  const svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%; height:auto; font:11px system-ui">
    <line x1="${pad-10}" y1="${midY}" x2="${W-pad+10}" y2="${midY}" stroke="#0f172a" stroke-width="1.2"/>
    ${[0,.25,.5,.75,1].map(t => {
      const yy = midY + (t-.5) * (H-2*pad) * 0;
      return '';
    }).join('')}
    <!-- Money in -->
    <rect x="${W*0.18}" y="${y(rev)}" width="${barW}" height="${midY - y(rev)}" fill="#10b981"/>
    <text x="${W*0.18 + barW/2}" y="${y(rev) - 6}" text-anchor="middle" font-weight="700" fill="#047857">${rev?fmtUsd(rev):'$0'}</text>
    <text x="${W*0.18 + barW/2}" y="${H - 14}" text-anchor="middle" fill="#0f172a" font-weight="600">Money in</text>
    ${rev===0 ? `<text x="${W*0.18 + barW/2}" y="${midY - 50}" text-anchor="middle" fill="#94a3b8" font-style="italic" font-size="10">no customer revenue yet</text>`:''}
    <!-- Money out (stacked) -->
    <rect x="${W*0.45}" y="${y(totals.internal_cost)}" width="${barW}" height="${midY - y(totals.internal_cost)}" fill="#ef4444"/>
    <rect x="${W*0.45}" y="${y(costT)}" width="${barW}" height="${y(totals.internal_cost) - y(costT)}" fill="#f97316"/>
    <text x="${W*0.45 + barW/2}" y="${y(costT) - 6}" text-anchor="middle" font-weight="700" fill="#b91c1c">${fmtUsd(costT)}</text>
    <text x="${W*0.45 + barW/2}" y="${midY - (midY - y(totals.internal_cost))/2}" text-anchor="middle" fill="#fff" font-size="10">${fmtUsd(totals.internal_cost)}</text>
    ${totals.customer_cost > 0 ? `<text x="${W*0.45 + barW/2}" y="${(y(costT) + y(totals.internal_cost))/2 + 4}" text-anchor="middle" fill="#fff" font-size="10">${fmtUsd(totals.customer_cost)}</text>` : ''}
    <text x="${W*0.45 + barW/2}" y="${H - 14}" text-anchor="middle" fill="#0f172a" font-weight="600">Money out</text>
    <!-- Net -->
    <rect x="${W*0.72}" y="${net >= 0 ? y(net) : midY}" width="${barW}" height="${Math.abs(midY - y(net))}" fill="${net>=0?'#059669':'#b91c1c'}" opacity="0.88"/>
    <text x="${W*0.72 + barW/2}" y="${net >= 0 ? y(net) - 10 : Math.min(H - 34, y(net) + 22)}" text-anchor="middle" font-weight="700" fill="${net>=0?'#059669':'#b91c1c'}">${((net>=0?'+':'-'))+fmtUsd(Math.abs(net)).slice(0)}</text>
    <text x="${W*0.72 + barW/2}" y="${H - 14}" text-anchor="middle" fill="#0f172a" font-weight="600">Net</text>
    <!-- zero-axis "1" reference under it -->
  </svg>`;
  $('pnl').innerHTML = svg;
}

render();
</script>
</body></html>
"""

html = HTML.replace('__PAYLOAD__', json.dumps(PAYLOAD, separators=(',', ':')))
with open(OUT, 'w') as f:
    f.write(html)
print(f'wrote {OUT}  ({len(html)/1024:.1f} KB, {len(rows)} fleet rows)')
