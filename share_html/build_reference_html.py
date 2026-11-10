#!/usr/bin/env python3 -I
"""Build share_html/GPU-LLM-Reference.html — static reference tables:
   A1 GPU prices (my quotes × public, per-GPU table)
   A2 my benchmark × InferenceX
   A3 InferenceX all-model frontier summary
   A4 OpenRouter weekly top-N (one sub-table per month)
No charts, no KPIs — just tables of record."""

import json, os, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT  = os.path.join(HERE, 'GPU-LLM-Reference.html')

def _find(name):
    for d in [os.path.join(ROOT, 'colab_upload', 'GPU-LLM-v2-Analytics-Colab 6'),
              os.path.join(ROOT, 'colab_upload'),
              os.path.join(ROOT, 'data'),
              os.path.join(ROOT, 'grid')]:
        p = os.path.join(d, name)
        if os.path.exists(p): return p
    raise FileNotFoundError(name)

payload = {}

# A1 — prices
my_q  = pd.read_csv(_find('my_gpu_opts.csv'))
pub_p = pd.read_csv(_find('public_gpu_prices.csv'))
keep = ['option_id','gpu_class','rental_term','listed_rate','upfront',
        'upfront_pct','price_date','source_url']
payload['a1_prices'] = pd.concat([
    my_q.assign(price_src='my_quotes')[keep + ['price_src']],
    pub_p.assign(price_src='public_market')[keep + ['price_src']],
], ignore_index=True).to_dict(orient='records')

# A2 — my bench × infx glm53
payload['a2_mybench'] = pd.read_csv(_find('my_glm53_b300_benchmark.csv')).to_dict(orient='records')
payload['a2_infx_glm'] = pd.read_csv(_find('infx_glm53_anchors.csv')).to_dict(orient='records')

# A3 — all models
payload['a3_all_models'] = pd.read_csv(_find('infx_all_models_anchors.csv')).to_dict(orient='records')

# A4 — openrouter weekly
or_df = pd.read_csv(_find('openrouter_weekly_top9_10-2025_to_10-2026.csv'))
payload['a4_or_weekly'] = {
    'model_col': or_df.columns[0],
    'week_cols': [c for c in or_df.columns[1:]],
    'rows': or_df.to_dict(orient='records'),
}

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reference Tables — GPU LLM</title>
<style>
  :root { --ink:#0f172a; --ink-2:#475569; --ink-3:#64748b; --line:#e2e8f0;
          --surface:#fff; --surface-2:#f8fafc; }
  * { box-sizing:border-box }
  body { margin:0; padding:0; background:#f1f5f9; color:var(--ink);
         font:14px/1.45 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif; }
  .wrap { max-width:1280px; margin:24px auto; padding:0 24px 60px; }
  h1 { font-size:17px; margin:0 0 4px; font-weight:700; }
  h2 { font-size:14px; font-weight:700; margin:32px 0 10px; color:var(--ink); }
  h3 { font-size:12.5px; font-weight:700; margin:18px 0 6px; color:var(--ink-2); }
  .sub { color:var(--ink-3); font-size:12px; margin-bottom:18px; }
  .card { background:var(--surface); border:1px solid var(--line); border-radius:10px;
          padding:14px 16px; margin-bottom:14px; box-shadow:0 1px 2px rgba(15,23,42,.04); }
  table { border-collapse:collapse; width:100%; font-size:12px; }
  thead th { background:var(--surface-2); color:var(--ink-3); font-size:10.5px;
             font-weight:600; text-transform:uppercase; letter-spacing:.05em;
             padding:7px 10px; text-align:right; border-bottom:1px solid var(--line); }
  tbody td { padding:5px 10px; text-align:right; border-top:1px solid #f1f5f9;
             font-variant-numeric:tabular-nums; }
  td.l, th.l { text-align:left }
  tr.my td { background:#fffbeb }
  tr.pub td { background:#f0f9ff }
  code { font-family:ui-monospace,S FMono-Regular,Menlo,Consolas,monospace; font-size:.92em; }
  a { color:#0369a1; }
</style></head>
<body><div class="wrap">
  <h1>Reference Tables</h1>
  <div class="sub">Appendix mirror from <code>GPU-LLM-v2-Analytics.ipynb</code> — A1 GPU prices · A2 my benchmark × InferenceX · A3 InferenceX all-model frontier · A4 OpenRouter weekly top-5 by month.</div>

  <h2>A1 · GPU prices — my quotes × public market</h2>
  <div class="card"><div id="a1"></div></div>

  <h2>A2 · My B300 benchmark × InferenceX GLM-5.3 anchor</h2>
  <div class="card"><h3>My lab measurements</h3><div id="a2mine"></div>
                    <h3>InferenceX anchor points (glm-5.3)</h3><div id="a2infx"></div></div>

  <h2>A3 · InferenceX — all-model anchors</h2>
  <div class="card"><div id="a3"></div></div>

  <h2>A4 · OpenRouter weekly top-5 models, by month</h2>
  <div class="card"><div id="a4"></div></div>
</div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
'use strict';
const P = JSON.parse(document.getElementById('payload').textContent);

function tbl(cols, rows, cls) {
  // cols: [{key, label, fmt(v, row) → html, align ('l'|'r')}]; rows: array of objects
  const thead = '<thead><tr>' + cols.map(c =>
    `<th class="${c.align==='l'?'l':''}">${c.label}</th>`).join('') + '</tr></thead>';
  const tbody = '<tbody>' + rows.map(r =>
    `<tr class="${cls ? cls(r) : ''}">${cols.map(c =>
      `<td class="${c.align==='l'?'l':''}">${c.fmt ? c.fmt(r[c.key], r) : (r[c.key] ?? '—')}</td>`).join('')}</tr>`).join('') + '</tbody>';
  return '<table>' + thead + tbody + '</table>';
}
const $ = id => document.getElementById(id);
const usd = (v, d=2) => (v==null||v===''||isNaN(v)) ? '—' : '$' + Number(v).toLocaleString('en-US', {maximumFractionDigits:d, minimumFractionDigits:d});
const num = (v, d=2) => (v==null||v===''||isNaN(v)) ? '—' : Number(v).toLocaleString('en-US', {maximumFractionDigits:d, minimumFractionDigits:d});

// A1 — prices per GPU class, sorted
{
  const rows = P.a1_prices.slice();
  const gpuOrder = ['gb300','b300','gb200','b200','h200','h100','mi355x','mi325x'];
  rows.sort((a, b) => gpuOrder.indexOf(a.gpu_class) - gpuOrder.indexOf(b.gpu_class)
                   || (+a.listed_rate) - (+b.listed_rate));
  $('a1').innerHTML = tbl([
    {key:'option_id', label:'offer', align:'l'},
    {key:'gpu_class', label:'gpu'},
    {key:'price_src', label:'src'},
    {key:'rental_term', label:'term'},
    {key:'listed_rate', label:'list $/h', fmt: v=>usd(v,2)},
    {key:'upfront', label:'upfront $', fmt: v=>usd(v,0)},
    {key:'upfront_pct', label:'upfront %', fmt: v=>v==null?'—':num(v,0)+'%'},
    {key:'price_date', label:'as of'},
  ], rows, r => r.price_src === 'my_quotes' ? 'my' : 'pub');
}

// A2 — two tables side by side
{
  $('a2mine').innerHTML = tbl(
    Object.keys(P.a2_mybench[0] || {}).map(k => ({key:k, label:k, align: typeof P.a2_mybench[0][k] === 'number' ? 'r' : 'l'})),
    P.a2_mybench);
  $('a2infx').innerHTML = tbl(
    Object.keys(P.a2_infx_glm[0] || {}).map(k => ({key:k, label:k, align: typeof P.a2_infx_glm[0][k] === 'number' ? 'r' : 'l'})),
    P.a2_infx_glm);
}

// A3 — all models
{
  const rows = P.a3_all_models;
  $('a3').innerHTML = tbl(
    Object.keys(rows[0] || {}).map(k => ({key:k, label:k, align: typeof rows[0][k] === 'number' ? 'r' : 'l'})),
    rows);
}

// A4 — openrouter weekly: group weeks by month, one table per month, top 5/week
{
  const weekCols = P.a4_or_weekly.week_cols;
  const rows     = P.a4_or_weekly.rows;
  const modelKey = P.a4_or_weekly.model_col;
  const months = {};
  for (const w of weekCols) months[w.slice(0,7)] = months[w.slice(0,7)] || [], months[w.slice(0,7)].push(w);
  let html = '';
  for (const ym of Object.keys(months).sort()) {
    const cols = months[ym];
    // rows in canonical table form: rows = week, cols = rank
    const topByWeek = cols.map(w => {
      const entries = rows
        .filter(r => r[modelKey] && !['Others','Total'].includes(r[modelKey]))
        .map(r => [r[modelKey], +r[w] || 0])
        .sort((a,b) => b[1] - a[1]).slice(0, 5);
      return { week: w, entries };
    });
    html += `<h3>${ym}</h3><table><thead><tr><th class="l">week of</th>` +
            [1,2,3,4,5].map(i => `<th class="l">#${i}</th>`).join('') + '</tr></thead><tbody>';
    for (const t of topByWeek) {
      html += `<tr><td class="l">${t.week}</td>` +
              [0,1,2,3,4].map(i => t.entries[i]
                ? `<td class="l">${t.entries[i][0]} <span style="color:var(--ink-3); font-size:10.5px;">(${t.entries[i][1].toFixed(1)}T)</span></td>`
                : '<td>—</td>').join('') + '</tr>';
    }
    html += '</tbody></table>';
  }
  $('a4').innerHTML = html;
}
</script>
</body></html>
"""

html = HTML.replace('__PAYLOAD__', json.dumps(payload, separators=(',',':'), default=str))
with open(OUT, 'w') as f: f.write(html)
print(f'wrote {OUT}  ({len(html)/1024:.1f} KB)')
