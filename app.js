/* ═══════════════════════════════════════════════════════
   THE STOREFRONT LEDGER — Midnight Edition · App Logic
   REAL FIGURES ONLY. Every number on the page comes from
   the live wire; when the wire is quiet, the page says so.
═══════════════════════════════════════════════════════ */

'use strict';

const state = { activeRange: '7D', loading: false, lastKpis: null, meta: null, localAuth: false };

const RANGE_WORDS = { '7D': 'THIS WEEK', '30D': 'THIS MONTH', 'MTD': 'MONTH TO DATE' };
const REFRESH_MS = 60000; // re-read the wire every minute

const LS_KEYS = 'ledger_ai_keys';
const LS_STAFF = 'ledger_staff';
const LS_SESSION = 'ledger_session';

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
      console.info('[Ledger] wire down:', json.error || 'no answer');
      setWire('down', json.error);
      renderQuiet();
      renderDiagnostics(json.stage === 'auth'
        ? [{ endpoint: 'Login with Amazon (auth)', ok: false, note: json.error || 'authentication failed' }]
        : null);
      return;
    }

    renderReal(json);
    renderDiagnostics(json.diagnostics);
    setWire('live');
    const syncEl = document.getElementById('colophonStatus');
    if (syncEl) syncEl.textContent = `Last read ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    console.info('[Ledger] wire unreachable:', err.message);
    setWire('down', err.message);
    renderQuiet();
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
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// ─── RENDER: REAL FIGURES ────────────────────────────
function renderMeta(meta) {
  state.meta = meta;
  setText('mastMode', meta.sandbox ? 'SANDBOX' : 'PRODUCTION');
  setText('colophonMeta', `Region ${String(meta.region || '—').toUpperCase()} · Marketplace ${meta.marketplace || '—'}`);
}

function renderReal(d) {
  const k = d.kpis || { revenue: 0, cogs: 0, fbaFees: 0, adSpend: 0, netProfit: 0, margin: 0, units: 0 };
  state.lastKpis = k;
  const period = RANGE_WORDS[state.activeRange] || state.activeRange;
  const orderCount = d.totalOrders ?? (d.orders?.length || 0);
  const quiet = k.revenue === 0 && orderCount === 0;

  // Lead story
  const lead = document.getElementById('leadProfit');
  if (lead) {
    lead.textContent = (k.netProfit < 0 ? '−' : '') + money(k.netProfit);
    lead.classList.toggle('loss', k.netProfit < 0);
  }
  setText('leadPeriod', period);
  if (quiet) {
    setText('leadHeadline', 'The wire is connected — and brought no sales for this period.');
    setText('leadDeck', 'That is Amazon’s real answer, not an error. Either there were no orders in this window, or the app’s data access is still awaiting approval in Seller Central.');
  } else {
    setText('leadHeadline',
      k.netProfit >= 0
        ? `Your store kept ${money(k.netProfit)} after every cost — ${fmt(k.units)} units across ${fmt(orderCount)} orders.`
        : `The store ran at a loss of ${money(k.netProfit)} this period against ${money(k.revenue)} in takings.`);
    setText('leadDeck',
      `Gross takings of ${money(k.revenue)}, less estimated goods (${money(k.cogs)}), fees (${money(k.fbaFees)}), and advertising (${money(k.adSpend)}). Live from Amazon.`);
  }

  // Stats
  setText('statRevenue', money(k.revenue));
  setText('statUnits', fmt(k.units));
  setText('statMargin', quiet ? '—' : `${k.margin}%`);
  setText('statMarginNote', quiet ? '' : 'est.');
  setText('statOrders', fmt(orderCount));

  // Board
  const bp = document.getElementById('boardProfit');
  if (bp) {
    bp.textContent = (k.netProfit < 0 ? '−' : '') + money(k.netProfit);
    bp.classList.toggle('spent', k.netProfit < 0);
  }
  setText('boardProfitNote', quiet ? 'no sales on the wire this period' : `net (est.) ${period.toLowerCase()} · margin ${k.margin}%`);
  setText('boardRevenue', money(k.revenue));
  setText('boardUnits', fmt(k.units));
  setText('boardOrders', fmt(orderCount));

  // Ledger + dollar split
  updateLedger(k);
  drawDollarSplit(k);

  // Shelf + order wire (only ever from real payloads)
  updateShelf(d.inventory || []);
  updateWireTable(d.orders || [], orderCount);

  // Dispatches from the real state of things
  renderDispatches(d, k, quiet);

  // Charts from real per-day figures (persisted history when we have it)
  renderCharts(d);

  // Fees: drop the "est." tag on the fee line when they're real from Amazon
  const feeTag = document.getElementById('feesEst');
  if (feeTag) feeTag.style.display = d.feesReal ? 'none' : '';
  const histNote = document.getElementById('historyNote');
  if (histNote) {
    const n = (d.history || []).length;
    histNote.textContent = n >= 2
      ? `Real history: ${n} day${n > 1 ? 's' : ''} recorded and counting.`
      : 'Real history begins recording now — the trend fills in day by day.';
  }

  // Verdict
  if (quiet) setVerdict('quiet');
  else setVerdict(k.netProfit >= 0 ? 'good' : 'trouble');
}

// When the wire itself is down (auth/network), print dashes — never inventions.
function renderQuiet() {
  ['leadProfit', 'statRevenue', 'statUnits', 'statMargin', 'statOrders',
   'boardProfit', 'boardRevenue', 'boardUnits', 'boardOrders'].forEach(id => setText(id, '—'));
  setText('leadHeadline', 'The wire could not be read.');
  setText('leadDeck', 'The connection to Amazon failed — the stamp above says so. No figures are shown because none were received.');
  setVerdict('down');
}

function setVerdict(kind) {
  const stamp = document.getElementById('verdictStamp');
  const line = document.getElementById('verdictLine');
  if (!stamp) return;
  stamp.classList.remove('trouble', 'caution');
  if (kind === 'trouble') {
    stamp.textContent = 'ATTENTION REQUIRED';
    stamp.classList.add('trouble');
    if (line) line.textContent = 'The house ran at a loss this period — open the Books and the Dispatches.';
  } else if (kind === 'quiet') {
    stamp.textContent = 'WIRE QUIET';
    stamp.classList.add('caution');
    if (line) line.textContent = 'Connected to Amazon, but no sales came over the wire for this period.';
  } else if (kind === 'down') {
    stamp.textContent = 'WIRE DOWN';
    stamp.classList.add('trouble');
    if (line) line.textContent = 'The connection to Amazon could not be read — see the stamp in the masthead.';
  } else {
    stamp.textContent = 'IN GOOD ORDER';
    if (line) line.textContent = 'The house is profitable and the wire is up.';
  }
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
}

function updateShelf(summaries) {
  const list = document.getElementById('shelfList');
  if (!list) return;

  if (!summaries.length) {
    list.innerHTML = '<p class="empty-note">No inventory reported on the wire.</p>';
    setText('boardShelf', '0');
    setText('boardShelfNote', 'no stock lines reported');
    return;
  }

  let low = 0, lowest = null;
  const html = summaries.slice(0, 8).map(item => {
    const qty  = item.totalQuantity || 0;
    const days = Math.round(qty / 5); // rough velocity placeholder until sales history accrues
    const pct  = Math.min(100, Math.round((days / 120) * 100));
    const cls  = days > 80 ? 'ok' : days > 40 ? 'low' : 'crit';
    if (cls !== 'ok') { low++; if (!lowest || days < lowest.days) lowest = { name: item.productName || item.asin, days }; }
    const name = esc(item.productName || item.sellerSku || item.asin || 'Unnamed product');

    return `<div class="shelf-row${cls !== 'ok' ? ' low' : ''}">
  <div class="shelf-name">${name} <span class="shelf-sku mono">${esc(item.asin || '')}</span></div>
  <div class="shelf-track"><span class="shelf-fill ${cls}" style="width:${pct}%"></span></div>
  <div class="shelf-days mono">${qty}<span class="d">u</span></div>
</div>`;
  }).join('');

  list.innerHTML = html;
  setText('boardShelf', String(summaries.length));
  setText('boardShelfNote', low ? `${low} line${low > 1 ? 's' : ''} running low` : 'stock lines reported');
}

function updateWireTable(orders, totalCount) {
  const tbody = document.getElementById('ordersBody');
  if (!tbody) return;

  if (!orders.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="empty-cell">No orders on the wire for this period.</td></tr>';
    return;
  }

  const html = orders.slice(0, 10).map(o => {
    const total  = o.OrderTotal?.Amount ? `$${esc(o.OrderTotal.Amount)}` : '—';
    const items  = (o.NumberOfItemsShipped || 0) + (o.NumberOfItemsUnshipped || 0);
    const status = o.OrderStatus || 'Pending';
    const cls    = status === 'Shipped' ? 'ok' : 'wait';
    const date   = o.PurchaseDate
      ? new Date(o.PurchaseDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      : '—';

    return `<tr>
  <td class="mono">${esc(o.AmazonOrderId || '—')}</td>
  <td>${date}</td>
  <td class="num mono">${items}</td>
  <td class="num mono">${total}</td>
  <td><span class="tag ${cls}">${esc(status)}</span></td>
</tr>`;
  }).join('');

  tbody.innerHTML = html + (totalCount > 10
    ? `<tr><td colspan="5" class="empty-cell">…and ${totalCount - 10} more in this period.</td></tr>` : '');
}

// ─── DISPATCHES — raised only by the real figures ────
function renderDispatches(d, k, quiet) {
  const row = document.getElementById('dispatchRow');
  if (!row) return;
  const items = [];

  if (quiet) {
    items.push({
      stamp: 'ATTEND', urgent: true,
      title: 'The wire brought no sales.',
      body: state.meta?.sandbox
        ? 'The house is still wired to Amazon’s sandbox — test service, no real history.'
        : 'Connected in production, yet no orders returned. Most often this means the app’s Orders data role is still awaiting approval in Seller Central.',
      action: state.meta?.sandbox
        ? '→ Flip to production once Amazon approves the app'
        : '→ Seller Central → Apps & Services → check the app’s data access',
    });
  }

  const unshipped = (d.orders || []).filter(o => o.OrderStatus && o.OrderStatus !== 'Shipped' && o.OrderStatus !== 'Canceled').length;
  if (unshipped) {
    items.push({
      stamp: 'THIS WEEK', urgent: false,
      title: `${unshipped} order${unshipped > 1 ? 's' : ''} not yet shipped.`,
      body: 'Open orders are waiting on fulfilment. Late dispatch is the fastest way to hurt account health.',
      action: '→ Review open orders in Seller Central',
    });
  }

  (d.inventory || []).forEach(item => {
    const qty = item.totalQuantity || 0;
    if (qty > 0 && qty < 20 && items.length < 5) {
      items.push({
        stamp: 'THIS WEEK', urgent: false,
        title: `${item.productName || item.asin || 'A product'} runs low.`,
        body: `Only ${qty} units reported in stock. Restocking takes weeks — the window to reorder is open now.`,
        action: '→ Plan a reorder before the shelf empties',
      });
    }
  });

  if (k.netProfit < 0 && !quiet) {
    items.push({
      stamp: 'ATTEND', urgent: true,
      title: 'The period ran at a loss.',
      body: `Costs outran ${money(k.revenue)} in takings by ${money(k.netProfit)}.`,
      action: '→ Open the Books and find the heaviest line',
    });
  }

  const badge = document.getElementById('dispatchCount');
  if (badge) { badge.textContent = String(items.length); badge.hidden = items.length === 0; }
  setText('boardActions', String(items.length));
  setText('boardActionsNote', items.length ? (items.some(i => i.urgent) ? 'one urgent' : 'none urgent') : 'nothing requires your signature');

  row.innerHTML = items.length
    ? items.map(i => `<article class="dispatch${i.urgent ? ' urgent' : ''}">
  <div class="dispatch-stamp${i.urgent ? '' : ' week'}">${i.stamp}</div>
  <h4 class="dispatch-title">${esc(i.title)}</h4>
  <p class="dispatch-body">${esc(i.body)}</p>
  <div class="dispatch-do">${esc(i.action)}</div>
</article>`).join('')
    : '<p class="empty-note">Nothing requires your signature. The wire is calm.</p>';
}

// ─── CHARTS — drawn only from real per-day figures ───
function renderCharts(d) {
  const daily = d.daily || [];
  const history = d.history || [];
  const trendBox = document.getElementById('chartTrend');
  const dailyBox = document.getElementById('chartDaily');
  const spark = document.getElementById('boardSpark');
  const emptyMsg = '<p class="chart-empty">No figures on the wire yet.</p>';
  const buildMsg = '<p class="chart-empty">Real history builds day by day — the line fills in as the days pass.</p>';

  // Trend: prefer the persisted multi-day NET-PROFIT history (real days
  // accumulating in the database). Fall back to this window's daily revenue.
  if (history.length >= 2) {
    drawTrend('chartTrend', history.map(h => h.net), history.map(h => h.day.slice(5)));
    drawSpark('boardSpark', history.map(h => h.net));
  } else if (daily.length) {
    drawTrend('chartTrend', daily.map(x => x.revenue), daily.map(x => x.date.slice(5)));
    drawSpark('boardSpark', daily.map(x => x.revenue));
  } else {
    if (trendBox) trendBox.innerHTML = history.length ? buildMsg : emptyMsg;
    if (spark) spark.innerHTML = '';
  }

  // Daily bars: this window's real per-day revenue.
  if (daily.length) {
    const values = daily.map(x => x.revenue);
    const labels = daily.map(x => x.date.slice(5));
    drawDaily('chartDaily', values.slice(-7), labels.slice(-7));
  } else if (dailyBox) {
    dailyBox.innerHTML = emptyMsg;
  }
}

function svgEl(container, html) {
  const box = document.getElementById(container);
  if (box) box.innerHTML = html;
}

function drawTrend(id, data, labels) {
  const W = 560, H = 150, PAD = 44, BOT = 22;
  const max = Math.max(...data, 1) * 1.15;
  const n = Math.max(data.length - 1, 1);
  const x = i => PAD + (i * (W - PAD - 10)) / n;
  const y = v => (H - BOT) - (v / max) * (H - BOT - 12);
  const pts = data.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const area = `M${x(0)},${y(data[0])} ${data.map((v, i) => `L${x(i)},${y(v)}`).join(' ')} L${x(data.length - 1)},${H - BOT} L${x(0)},${H - BOT} Z`;
  const grid = [0.5, 1].map(f => {
    const val = max * f / 1.15;
    const gy = y(val);
    return `<line x1="${PAD}" y1="${gy}" x2="${W - 10}" y2="${gy}" class="c-grid"/>
<text x="${PAD - 6}" y="${gy + 3}" class="c-label" text-anchor="end">$${fmt(val)}</text>`;
  }).join('');
  const last = data.length - 1;

  svgEl(id, `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
<defs><linearGradient id="tfill" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0%" stop-color="#58b98a" stop-opacity="0.28"/>
  <stop offset="100%" stop-color="#58b98a" stop-opacity="0"/>
</linearGradient></defs>
${grid}
<path d="${area}" fill="url(#tfill)"/>
<polyline points="${pts}" class="c-line"/>
<circle cx="${x(last)}" cy="${y(data[last])}" r="3.5" class="c-dot"/>
<text x="${x(0)}" y="${H - 6}" class="c-label">${labels[0] || ''}</text>
<text x="${x(last)}" y="${H - 6}" class="c-label" text-anchor="end">${labels[last] || ''}</text>
</svg>`);
}

function drawDaily(id, values, labels) {
  const W = 560, H = 150, PAD = 20, BOT = 24;
  const max = Math.max(...values, 1) * 1.2;
  const bw = (W - PAD - 14) / values.length;
  const best = Math.max(...values);
  const bars = values.map((v, i) => {
    const bh = (v / max) * (H - BOT - 16);
    const bx = PAD + i * bw + bw * 0.14;
    const by = (H - BOT) - bh;
    return `<rect x="${bx.toFixed(1)}" y="${by.toFixed(1)}" width="${(bw * 0.72).toFixed(1)}" height="${Math.max(bh, 1).toFixed(1)}" rx="2" class="c-bar${v === best && v > 0 ? ' best' : ''}"/>
<text x="${(bx + bw * 0.36).toFixed(1)}" y="${by - 5}" class="c-label" text-anchor="middle">$${fmt(v)}</text>
<text x="${(bx + bw * 0.36).toFixed(1)}" y="${H - 8}" class="c-label" text-anchor="middle">${labels[i] || ''}</text>`;
  }).join('');
  svgEl(id, `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
<line x1="${PAD}" y1="${H - 24}" x2="${W - 10}" y2="${H - 24}" class="c-axis"/>
${bars}
</svg>`);
}

function drawSpark(id, data) {
  if (data.length < 2) { svgEl(id, ''); return; }
  const W = 220, H = 44;
  const max = Math.max(...data), min = Math.min(...data);
  const x = i => (i * W) / (data.length - 1);
  const y = v => H - 4 - ((v - min) / (max - min || 1)) * (H - 10);
  const pts = data.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  svgEl(id, `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
<polyline points="${pts}" class="c-line thin"/>
<circle cx="${W}" cy="${y(data[data.length - 1])}" r="2.5" class="c-dot"/>
</svg>`);
}

function drawDollarSplit(k) {
  const box = document.getElementById('dollarSplit');
  if (!box) return;
  if (!k.revenue) {
    box.innerHTML = '<p class="empty-note">Awaiting live sales.</p>';
    return;
  }
  const parts = [
    { key: 'Goods', val: k.cogs, cls: 'sp-goods' },
    { key: 'Fees',  val: k.fbaFees, cls: 'sp-fees' },
    { key: 'Ads',   val: k.adSpend, cls: 'sp-ads' },
    { key: 'Kept',  val: Math.max(k.netProfit, 0), cls: 'sp-kept' },
  ];
  const total = parts.reduce((s, p) => s + p.val, 0) || 1;
  const bar = parts.map(p =>
    `<span class="split-seg ${p.cls}" style="width:${((p.val / total) * 100).toFixed(1)}%" title="${p.key}"></span>`
  ).join('');
  const legend = parts.map(p =>
    `<span class="split-key"><span class="split-swatch ${p.cls}"></span>${p.key} <b class="mono">${Math.round((p.val / total) * 100)}¢</b></span>`
  ).join('');
  box.innerHTML = `<div class="split-bar">${bar}</div><div class="split-legend">${legend}</div>
<p class="footnote">Of every dollar the store takes in, this is how it divides (cost lines estimated until the Finances API is connected). The green is yours.</p>`;
}

// ─── DIAGNOSTICS — which endpoints answered, and why not ─
function renderDiagnostics(diag) {
  const box = document.getElementById('diagList');
  if (!box) return;
  if (!diag || !diag.length) {
    box.innerHTML = '<p class="empty-note">No diagnostics received.</p>';
    return;
  }
  box.innerHTML = diag.map(d => `<div class="diag-row ${d.ok ? 'ok' : 'bad'}">
  <span class="diag-mark">${d.ok ? '✓' : '✗'}</span>
  <span class="diag-name">${esc(d.endpoint)}${d.status ? ` <span class="diag-code mono">${d.status}</span>` : ''}</span>
  <span class="diag-note">${esc(d.note || '')}</span>
</div>`).join('');
}

// ─── WIRE STATUS (the stamp — always honest) ─────────
function setWire(status, detail) {
  const stamp = document.getElementById('wireStamp');
  const colophon = document.getElementById('colophonStatus');
  if (!stamp) return;
  const sandbox = state.meta ? !!state.meta.sandbox : false;

  stamp.classList.remove('demo', 'error');
  if (status === 'live' && !sandbox) {
    stamp.textContent = 'WIRE · LIVE FROM AMAZON';
    setText('boardWire', 'LIVE');
    setText('boardWireNote', 'real figures, straight from Amazon');
  } else if (status === 'live') {
    stamp.textContent = 'WIRE · SANDBOX TEST';
    stamp.classList.add('demo');
    setText('boardWire', 'SANDBOX');
    setText('boardWireNote', 'connected — Amazon test service');
  } else if (status === 'syncing') {
    stamp.textContent = 'WIRE · RECEIVING…';
  } else {
    stamp.textContent = 'WIRE · DOWN';
    stamp.classList.add('error');
    setText('boardWire', 'DOWN');
    setText('boardWireNote', detail ? String(detail).slice(0, 60) : 'connection failed');
    if (colophon) colophon.textContent = 'The wire could not be read';
  }
}

// ─── FROM THE EDITOR (Gemini / Groq) ─────────────────
function getOwnKeys() {
  try { return JSON.parse(localStorage.getItem(LS_KEYS) || '{}'); }
  catch { return {}; }
}

async function fetchEditorial() {
  const btn = document.getElementById('rewriteBtn');
  if (btn) { btn.disabled = true; btn.textContent = '… the editor is writing'; }
  try {
    const res = await fetch('/.netlify/functions/ai-editor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        range: state.activeRange,
        period: RANGE_WORDS[state.activeRange] || state.activeRange,
        kpis: state.lastKpis,
        keys: getOwnKeys(),
      }),
    });
    const json = await res.json();
    if (!json.success || !json.paragraphs?.length) {
      console.info('[Ledger] editor unavailable:', json.error || 'no text');
      setText('boardEditor', 'SILENT');
      return;
    }

    const body = document.querySelector('.editorial-body');
    if (body) {
      body.innerHTML = json.paragraphs.map((p, i) => {
        const safe = esc(p);
        if (i === 0 && safe.length > 1) {
          return `<p><span class="dropcap">${safe[0]}</span>${safe.slice(1)}</p>`;
        }
        return `<p>${safe}</p>`;
      }).join('');
    }
    const sig = document.querySelector('.editorial-sig');
    if (sig) sig.textContent = `— The Ledger · written by ${json.model || 'AI'} from this period's live figures`;
    setText('boardEditor', 'FRESH');
  } catch (err) {
    console.info('[Ledger] editor unavailable:', err.message);
    setText('boardEditor', 'SILENT');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '↻ Ask the editor to write again'; }
  }
}

function refreshEditorial() { fetchEditorial(); }

// ─── SETTINGS: OWN KEYS ──────────────────────────────
function saveKeys() {
  const gemini = document.getElementById('keyGemini')?.value.trim();
  const groq = document.getElementById('keyGroq')?.value.trim();
  const keys = {};
  if (gemini) keys.gemini = gemini;
  if (groq) keys.groq = groq;
  localStorage.setItem(LS_KEYS, JSON.stringify(keys));
  reflectKeyStatus();
  fetchEditorial();
}

function clearKeys() {
  localStorage.removeItem(LS_KEYS);
  const g = document.getElementById('keyGemini'); if (g) g.value = '';
  const q = document.getElementById('keyGroq'); if (q) q.value = '';
  reflectKeyStatus();
}

function reflectKeyStatus() {
  const keys = getOwnKeys();
  const parts = [];
  if (keys.gemini) parts.push('Gemini');
  if (keys.groq) parts.push('Groq');
  setText('keysStatus', parts.length
    ? `Using YOUR ${parts.join(' and ')} key${parts.length > 1 ? 's' : ''} (saved in this browser).`
    : 'Using the paper’s house keys.');

  // Confirm the house keys really are stored on the server — proof they exist
  // without ever showing the secret values.
  fetch('/.netlify/functions/ai-editor', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'keystatus' }),
  }).then(r => r.json()).then(s => {
    const el = document.getElementById('houseKeyStatus');
    if (!el) return;
    if (s?.success) {
      el.innerHTML =
        `House Gemini key: <b class="${s.houseGemini ? 'kept' : 'spent'}">${s.houseGemini ? 'STORED ✓' : 'missing ✗'}</b>` +
        ` &nbsp;·&nbsp; House Groq key: <b class="${s.houseGroq ? 'kept' : 'spent'}">${s.houseGroq ? 'STORED ✓' : 'missing ✗'}</b>`;
    } else {
      el.textContent = 'Could not reach the key service.';
    }
  }).catch(() => {});
}

// ─── STAFF & SESSIONS (Supabase via /staff) ──────────
const API_STAFF = '/.netlify/functions/staff';

async function staffApi(action, payload = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 12000);
  try {
    const res = await fetch(API_STAFF, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, token: getSession()?.token, ...payload }),
      signal: ctrl.signal,
    });
    return await res.json();
  } catch (err) {
    return { success: false, error: err.name === 'AbortError' ? 'the house is waking — try once more' : err.message };
  } finally {
    clearTimeout(timer);
  }
}

function getStaffLocal() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_STAFF) || 'null');
    if (Array.isArray(s)) return s;
  } catch { /* fall through */ }
  return [];
}

function roleClass(role) {
  return { 'Proprietor': 'proprietor', 'Keeper of Books': 'keeper', 'Clerk': 'clerk', 'Reader': 'reader' }[role] || 'reader';
}

function paintStaff(staff, serverBacked) {
  const list = document.getElementById('registryList');
  if (!list) return;
  list.innerHTML = staff.length
    ? staff.map((p) => `<div class="registry-row">
  <div class="rr-who">
    <div class="rr-name">${esc(p.name)}</div>
    <div class="rr-email">${esc(p.email || '')}</div>
  </div>
  <span class="rr-role ${roleClass(p.role)}">${esc(p.role)}</span>
  <button class="rr-remove" onclick="removeStaff('${esc(p.id ?? '')}')" title="Strike from the book">strike</button>
</div>`).join('')
    : '<div class="registry-empty">The book is empty — enter the first name.</div>';
  setText('boardStaff', String(staff.length));
  const status = document.getElementById('staffStatus');
  if (status && !serverBacked) status.textContent = 'Backend unreachable — registry running in this browser only.';
}

async function renderStaff() {
  if (!state.localAuth) {
    const json = await staffApi('list');
    if (json?.success) { paintStaff(json.staff, true); return; }
  }
  paintStaff(getStaffLocal(), false);
}

async function addStaff() {
  const name = document.getElementById('staffName')?.value.trim();
  const email = document.getElementById('staffEmail')?.value.trim();
  const role = document.getElementById('staffRole')?.value || 'Reader';
  const pass = document.getElementById('staffPass')?.value || '';
  const status = document.getElementById('staffStatus');
  const say = (m, ok) => { if (status) { status.textContent = m; status.style.color = ok ? 'var(--kept)' : 'var(--spent)'; } };

  if (!name) return say('A name is required to enter the book.');
  if (pass.length < 4) return say('A passcode of at least 4 characters is required.');

  const json = await staffApi('add', { name, email, role, pass });
  if (!json.success) return say(json.error || 'The book refused the entry.');

  ['staffName', 'staffEmail', 'staffPass'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  say(`${name} entered as ${role}. They can now sign in.`, true);
  renderStaff();
}

async function removeStaff(id) {
  const status = document.getElementById('staffStatus');
  const json = await staffApi('remove', { id });
  if (!json.success && status) { status.textContent = json.error || 'Could not strike the name.'; status.style.color = 'var(--spent)'; }
  renderStaff();
}

// ─── THE GATE ────────────────────────────────────────
function getSession() {
  try { return JSON.parse(localStorage.getItem(LS_SESSION) || 'null'); }
  catch { return null; }
}

function showGateForm(hasKeeper) {
  document.getElementById('gateSetup').hidden = hasKeeper;
  document.getElementById('gateLogin').hidden = !hasKeeper;
}

async function gateShow() {
  const gate = document.getElementById('gate');
  if (!gate) return;

  const knownKeeper = getStaffLocal().some(p => p.passHash) || !!localStorage.getItem('ledger_has_keeper');
  showGateForm(knownKeeper);
  gate.hidden = false;
  gate.style.display = 'flex';
  document.body.classList.add('gated');

  const status = await staffApi('status');
  if (status?.success) {
    state.localAuth = false;
    localStorage.setItem('ledger_has_keeper', status.hasKeeper ? '1' : '');
    showGateForm(status.hasKeeper);
  } else {
    state.localAuth = true;
    showGateForm(knownKeeper);
  }
}

function gateHide(session) {
  const gate = document.getElementById('gate');
  if (gate) { gate.hidden = true; gate.style.display = 'none'; }
  document.body.classList.remove('gated');
  if (session) setText('mastReader', `KEPT BY ${session.name.toUpperCase()}`);
}

async function sha256(text) {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function gateCreate(e) {
  e.preventDefault();
  const name = document.getElementById('setupName')?.value.trim();
  const pass = document.getElementById('setupPass')?.value || '';
  const status = document.getElementById('setupStatus');
  const say = (m) => { if (status) { status.textContent = m; status.style.color = 'var(--spent)'; } };
  if (!name || pass.length < 4) return (say('A name and a passcode of at least 4 characters, please.'), false);

  if (!state.localAuth) {
    const json = await staffApi('bootstrap', { name, pass });
    if (!json.success) return (say(json.error || 'The house could not be opened.'), false);
    const session = { name: json.name, role: json.role, token: json.token };
    localStorage.setItem(LS_SESSION, JSON.stringify(session));
    localStorage.setItem('ledger_has_keeper', '1');
    gateHide(session);
    renderStaff();
    return false;
  }
  const staff = getStaffLocal();
  staff.unshift({ name, email: '', role: 'Proprietor', passHash: await sha256(pass) });
  localStorage.setItem(LS_STAFF, JSON.stringify(staff));
  const session = { name, role: 'Proprietor' };
  localStorage.setItem(LS_SESSION, JSON.stringify(session));
  gateHide(session);
  renderStaff();
  return false;
}

async function gateEnter(e) {
  e.preventDefault();
  const who = (document.getElementById('loginName')?.value || '').trim();
  const pass = document.getElementById('loginPass')?.value || '';
  const status = document.getElementById('loginStatus');
  const say = (m) => { if (status) { status.textContent = m; status.style.color = 'var(--spent)'; } };

  if (!state.localAuth) {
    const json = await staffApi('login', { who, pass });
    if (!json.success) return (say(json.error || 'The book does not recognise that name and passcode.'), false);
    const session = { name: json.name, role: json.role, token: json.token };
    localStorage.setItem(LS_SESSION, JSON.stringify(session));
    gateHide(session);
    renderStaff();
    return false;
  }
  const hash = await sha256(pass);
  const match = getStaffLocal().find(p =>
    (p.name.toLowerCase() === who.toLowerCase() || (p.email || '').toLowerCase() === who.toLowerCase()) && p.passHash === hash
  );
  if (!match) return (say('The book does not recognise that name and passcode.'), false);
  const session = { name: match.name, role: match.role };
  localStorage.setItem(LS_SESSION, JSON.stringify(session));
  gateHide(session);
  renderStaff();
  return false;
}

async function gateSignOut() {
  const token = getSession()?.token;
  if (token && !state.localAuth) await staffApi('signout', { token });
  localStorage.removeItem(LS_SESSION);
  gateShow();
}

// ─── TABS ────────────────────────────────────────────
function showTab(btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const panel = document.getElementById(`tab-${btn.dataset.tab}`);
  if (panel) panel.classList.add('active');
}

function showTabByName(name) {
  const btn = document.querySelector(`.tab[data-tab="${name}"]`);
  if (btn) showTab(btn);
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

  reflectKeyStatus();

  const session = getSession();
  if (session?.token) {
    gateShow();
    staffApi('verify', { token: session.token }).then(res => {
      if (res?.success) {
        state.localAuth = false;
        gateHide({ name: res.name, role: res.role, token: session.token });
        renderStaff();
      } else {
        localStorage.removeItem(LS_SESSION);
      }
    });
  } else if (session && getStaffLocal().some(p => p.passHash)) {
    state.localAuth = true;
    gateHide(session);
    renderStaff();
  } else {
    gateShow();
  }

  fetchData(state.activeRange);
  fetchEditorial();
  setInterval(() => fetchData(state.activeRange), REFRESH_MS);
  console.log('[The Storefront Ledger] midnight edition — real figures only');
});
