/* ═══════════════════════════════════════════════════════
   FBA INTELLIGENCE TERMINAL — App Logic
   SP-API live data via /.netlify/functions/sp-api-data
═══════════════════════════════════════════════════════ */

'use strict';

// ─── STATE ───────────────────────────────────────────
const state = {
  activeView: 'overview',
  activeRange: '7D',
  data: null,
  loading: false,
};

// ─── SP-API FETCH ────────────────────────────────────
async function fetchData(range) {
  if (state.loading) return;
  state.loading = true;
  setSyncStatus('syncing');

  try {
    const res  = await fetch(`/.netlify/functions/sp-api-data?range=${range}`);
    const json = await res.json();
    if (!json.success) throw new Error(json.error || 'API returned failure');

    state.data = json;
    renderDashboard(json);
    setSyncStatus('live');

    const syncEl = document.querySelector('.sync-time');
    if (syncEl) syncEl.textContent = 'SYNC just now';
  } catch (err) {
    console.error('[FBA] fetch error:', err.message);
    setSyncStatus('error');
  } finally {
    state.loading = false;
  }
}

// ─── RENDER ──────────────────────────────────────────
function fmt(n) {
  return new Intl.NumberFormat('en-US').format(Math.round(n || 0));
}

function renderDashboard(d) {
  const { kpis, inventory } = d;
  // Only overwrite the dashboard if the sandbox actually returned sales data.
  // An empty sandbox response (revenue 0) would otherwise blank out the demo.
  if (kpis && kpis.revenue > 0) {
    updateKPICards(kpis);
    updateTicker(kpis);
    updateWaterfall(kpis);
  }
  if (inventory?.length) updateInventory(inventory);
  updateAlertBadge();
}

function updateKPICards(kpis) {
  // Card order in HTML: profit, revenue, margin, units, fbaFees
  const values = [
    `$${fmt(kpis.netProfit)}`,
    `$${fmt(kpis.revenue)}`,
    `${kpis.margin}%`,
    fmt(kpis.units),
    `$${fmt(kpis.fbaFees)}`,
  ];
  document.querySelectorAll('.kpi-card .kpi-value').forEach((el, i) => {
    if (values[i] !== undefined) el.textContent = values[i];
  });
  document.querySelectorAll('.kpi-card .kpi-period').forEach(el => {
    el.textContent = state.activeRange;
  });
}

function updateTicker(kpis) {
  const items = document.querySelectorAll('.ticker-item');
  const ticks = [
    { label: `NET PROFIT (${state.activeRange})`, val: `$${fmt(kpis.netProfit)}`, dir: kpis.netProfit >= 0 ? 'up' : 'dn' },
    { label: 'REVENUE',    val: `$${fmt(kpis.revenue)}`,  dir: 'up' },
    { label: 'AVG MARGIN', val: `${kpis.margin}%`,         dir: kpis.margin >= 20 ? 'up' : 'dn' },
    { label: 'UNITS SOLD', val: fmt(kpis.units),            dir: 'up' },
    { label: 'FBA FEES',   val: `$${fmt(kpis.fbaFees)}`,   dir: 'dn' },
  ];
  items.forEach((el, i) => {
    if (!ticks[i]) return;
    const t = ticks[i];
    el.className = `ticker-item tick-${t.dir}`;
    el.innerHTML = `${t.label} <b>${t.val}</b>`;
  });
}

function updateWaterfall(kpis) {
  document.querySelectorAll('.wf-row').forEach(row => {
    const label = row.querySelector('.wf-label')?.textContent?.trim();
    const valEl = row.querySelector('.wf-val');
    if (!valEl) return;
    if (label === 'GROSS REVENUE') valEl.textContent = `$${fmt(kpis.revenue)}`;
    if (label === 'COGS (WAC)')    valEl.textContent = `-$${fmt(kpis.cogs)}`;
    if (label === 'FBA FEES')      valEl.textContent = `-$${fmt(kpis.fbaFees)}`;
    if (label === 'AD SPEND')      valEl.textContent = `-$${fmt(kpis.adSpend)}`;
    if (label === 'NET PROFIT')    valEl.textContent = `$${fmt(kpis.netProfit)}`;
  });
  const marginEl = document.querySelector('.wf-margin');
  if (marginEl && kpis.margin !== undefined) {
    marginEl.innerHTML = `MARGIN <b class="green">${kpis.margin}%</b>`;
  }
}

function updateInventory(summaries) {
  const list = document.querySelector('.inv-list');
  if (!list) return;

  const html = summaries.slice(0, 5).map(item => {
    const qty   = item.totalQuantity || 0;
    const days  = Math.round(qty / 5); // placeholder daily velocity
    const pct   = Math.min(100, Math.round((days / 120) * 100));
    const color = days > 80 ? 'green' : days > 40 ? 'amber' : 'red';
    const badge = days > 80 ? 'OK' : days > 40 ? 'REORDER' : 'CRITICAL';
    const name  = item.productName || item.sellerSku || item.asin;

    return `<div class="inv-row${color !== 'green' ? ' flagged' : ''}">
  <div class="inv-info">
    <span class="inv-name">${name}</span>
    <span class="inv-sku mono">${item.asin}</span>
  </div>
  <div class="inv-bar-wrap"><div class="inv-bar ${color}" style="width:${pct}%"></div></div>
  <span class="inv-days mono ${color}">${days}d</span>
  <span class="status-pill ${color} sm">${badge}</span>
</div>`;
  }).join('');

  if (html) list.innerHTML = html;
}

// ─── STATUS HELPERS ──────────────────────────────────
function setSyncStatus(status) {
  const live   = document.querySelector('.live-badge');
  const apiRow = [...document.querySelectorAll('.status-row')]
    .find(r => r.querySelector('.sd')?.textContent === 'API');
  const sv = apiRow?.querySelector('.sv');

  if (status === 'live') {
    if (live) live.innerHTML = '<span class="live-dot"></span>LIVE';
    if (sv) { sv.textContent = 'CONNECTED'; sv.className = 'sv ok'; }
  } else if (status === 'syncing') {
    if (live) live.innerHTML = '<span class="live-dot" style="background:var(--amber)"></span>SYNCING';
    if (sv) { sv.textContent = 'SYNCING'; sv.className = 'sv'; }
  } else {
    if (live) live.innerHTML = '<span class="live-dot" style="background:var(--red)"></span>ERROR';
    if (sv) { sv.textContent = 'ERROR'; sv.className = 'sv'; }
  }
}

// ─── VIEW ROUTER ─────────────────────────────────────
function showView(viewId) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  const target = document.getElementById(`view-${viewId}`);
  if (target) target.classList.add('active');

  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('onclick')?.includes(`'${viewId}'`)) item.classList.add('active');
  });

  state.activeView = viewId;
}

// ─── RANGE SELECTOR ──────────────────────────────────
function setRange(btn, range) {
  document.querySelectorAll('.rtab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  state.activeRange = range;
  fetchData(range);
}

// ─── ALERT BADGE ─────────────────────────────────────
function updateAlertBadge() {
  const badge = document.getElementById('alertBadge');
  if (badge) badge.textContent = '3 ALERTS';
}

// ─── INIT ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateAlertBadge();

  const aiBtn = document.querySelector('.ai-refresh-btn');
  if (aiBtn) {
    aiBtn.addEventListener('click', () => {
      aiBtn.textContent = 'GENERATING...';
      aiBtn.disabled = true;
      setTimeout(() => { aiBtn.textContent = 'REFRESH NOW'; aiBtn.disabled = false; }, 2000);
    });
  }

  fetchData(state.activeRange);
  console.log('[FBA Intelligence Terminal] initialized — fetching SP-API sandbox data');
});
