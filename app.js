/* ═══════════════════════════════════════════════════════
   THE STOREFRONT LEDGER — App Logic
   SP-API live data via /.netlify/functions/sp-api-data
═══════════════════════════════════════════════════════ */

'use strict';

const state = { activeRange: '7D', loading: false };

const RANGE_WORDS = { '7D': 'THIS WEEK', '30D': 'THIS MONTH', 'MTD': 'MONTH TO DATE' };

// ─── FETCH ───────────────────────────────────────────
async function fetchData(range) {
  if (state.loading) return;
  state.loading = true;
  setWire('syncing');

  try {
    const res  = await fetch(`/.netlify/functions/sp-api-data?range=${range}`);
    const json = await res.json();

    if (json.meta) renderMeta(json.meta);

    if (!json.success) {
      // Credentials or sandbox not returning data — the paper still prints,
      // clearly stamped as a proof copy.
      console.info('[Ledger] live data unavailable:', json.error || 'no data');
      setWire('demo');
      return;
    }

    renderLive(json);
    setWire('live');
  } catch (err) {
    console.info('[Ledger] printing from demonstration figures:', err.message);
    setWire('demo');
  } finally {
    state.loading = false;
  }
}

// ─── HELPERS ─────────────────────────────────────────
function fmt(n) {
  return new Intl.NumberFormat('en-US').format(Math.round(n || 0));
}
function money(n) { return `$${fmt(Math.abs(n))}`; }
function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

// ─── RENDER ──────────────────────────────────────────
function renderMeta(meta) {
  setText('mastMode', meta.sandbox ? 'SANDBOX EDITION' : 'PRODUCTION EDITION');
  setText('colophonMeta', `Region ${String(meta.region || '—').toUpperCase()} · Marketplace ${meta.marketplace || '—'}`);
}

function renderLive(d) {
  const k = d.kpis;
  // An empty sandbox answer (revenue 0) keeps the demonstration figures —
  // never print a blank front page.
  if (k && k.revenue > 0) {
    const profit = k.netProfit;
    const lead = document.getElementById('leadProfit');
    if (lead) {
      lead.textContent = (profit < 0 ? '−' : '') + money(profit);
      lead.classList.toggle('loss', profit < 0);
    }
    setText('leadPeriod', RANGE_WORDS[state.activeRange] || state.activeRange);
    setText('leadHeadline',
      profit >= 0
        ? `Your store kept ${money(profit)} after every cost — a ${k.margin}% margin on ${fmt(k.units)} units sold.`
        : `The store ran at a loss of ${money(profit)} this period — costs outran ${money(k.revenue)} in takings.`);
    setText('leadDeck',
      `Gross takings of ${money(k.revenue)}, less goods (${money(k.cogs)}), fulfilment & fees (${money(k.fbaFees)}), and advertising (${money(k.adSpend)}). Figures live from Amazon.`);

    setText('statRevenue', money(k.revenue));
    setText('statUnits', fmt(k.units));
    setText('statMargin', `${k.margin}%`);

    updateLedger(k);
  }

  if (d.inventory?.length) updateShelf(d.inventory);
  if (d.orders?.length) updateWire(d.orders);
}

function updateLedger(k) {
  const rows = {
    revenue:  { val: k.revenue,  sign: '' },
    cogs:     { val: k.cogs,     sign: '−' },
    fbaFees:  { val: k.fbaFees,  sign: '−' },
    adSpend:  { val: k.adSpend,  sign: '−' },
    netProfit:{ val: k.netProfit, sign: k.netProfit < 0 ? '−' : '' },
  };
  document.querySelectorAll('[data-ledger]').forEach(el => {
    const r = rows[el.dataset.ledger];
    if (r) el.textContent = `${r.sign}${money(r.val)}`;
  });
  const max = Math.max(k.revenue, 1);
  const widths = { revenue: k.revenue, cogs: k.cogs, fbaFees: k.fbaFees, adSpend: k.adSpend, netProfit: Math.max(k.netProfit, 0) };
  document.querySelectorAll('#ledgerTable tr').forEach(tr => {
    const key = tr.querySelector('[data-ledger]')?.dataset.ledger;
    const bar = tr.querySelector('.bar');
    if (key && bar && widths[key] !== undefined) {
      bar.style.width = `${Math.min(100, Math.round((widths[key] / max) * 100))}%`;
    }
  });
  const m = document.getElementById('ledgerMargin');
  if (m) m.textContent = `${k.margin}%`;
}

function updateShelf(summaries) {
  const list = document.getElementById('shelfList');
  if (!list) return;

  const html = summaries.slice(0, 6).map(item => {
    const qty  = item.totalQuantity || 0;
    const days = Math.round(qty / 5); // placeholder daily velocity
    const pct  = Math.min(100, Math.round((days / 120) * 100));
    const cls  = days > 80 ? 'ok' : days > 40 ? 'low' : 'crit';
    const name = item.productName || item.sellerSku || item.asin || 'Unnamed product';

    return `<div class="shelf-row${cls !== 'ok' ? ' low' : ''}">
  <div class="shelf-name">${name} <span class="shelf-sku mono">${item.asin || ''}</span></div>
  <div class="shelf-track"><span class="shelf-fill ${cls}" style="width:${pct}%"></span></div>
  <div class="shelf-days mono">${days}<span class="d">d</span></div>
</div>`;
  }).join('');

  if (html) list.innerHTML = html;
}

function updateWire(orders) {
  const tbody = document.getElementById('ordersBody');
  if (!tbody) return;

  const html = orders.slice(0, 8).map(o => {
    const total  = o.OrderTotal?.Amount ? `$${o.OrderTotal.Amount}` : '—';
    const items  = (o.NumberOfItemsShipped || 0) + (o.NumberOfItemsUnshipped || 0);
    const status = o.OrderStatus || 'Pending';
    const cls    = status === 'Shipped' ? 'ok' : 'wait';
    const date   = o.PurchaseDate
      ? new Date(o.PurchaseDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      : '—';

    return `<tr>
  <td class="mono">${o.AmazonOrderId || '—'}</td>
  <td>${date}</td>
  <td class="num mono">${items}</td>
  <td class="num mono">${total}</td>
  <td><span class="tag ${cls}">${status}</span></td>
</tr>`;
  }).join('');

  if (html) tbody.innerHTML = html;
}

// ─── WIRE STATUS (the stamp) ─────────────────────────
function setWire(status) {
  const stamp = document.getElementById('wireStamp');
  const colophon = document.getElementById('colophonStatus');
  if (!stamp) return;

  stamp.classList.remove('demo', 'error');
  if (status === 'live') {
    stamp.textContent = 'WIRE · LIVE FROM AMAZON';
    if (colophon) colophon.textContent = 'Printed from live figures';
  } else if (status === 'syncing') {
    stamp.textContent = 'WIRE · RECEIVING…';
  } else if (status === 'demo') {
    stamp.textContent = 'PRESS PROOF · DEMO FIGURES';
    stamp.classList.add('demo');
    if (colophon) colophon.textContent = 'Printed from demonstration figures';
  } else {
    stamp.textContent = 'WIRE · DOWN';
    stamp.classList.add('error');
  }
}

// ─── EDITIONS (range) ────────────────────────────────
function setRange(btn, range) {
  document.querySelectorAll('.edition').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  state.activeRange = range;
  setText('leadPeriod', RANGE_WORDS[range] || range);
  fetchData(range);
}

// ─── INIT ────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const now = new Date();
  setText('mastDate', now.toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  }));

  fetchData(state.activeRange);
  console.log('[The Storefront Ledger] first edition printed');
});
