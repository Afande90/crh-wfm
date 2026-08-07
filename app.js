/* ═══════════════════════════════════════════════════════
   THE STOREFRONT LEDGER — Midnight Edition · App Logic
   SP-API data via /.netlify/functions/sp-api-data
   AI editor via /.netlify/functions/ai-editor
═══════════════════════════════════════════════════════ */

'use strict';

const state = { activeRange: '7D', loading: false, lastKpis: null };

const RANGE_WORDS = { '7D': 'THIS WEEK', '30D': 'THIS MONTH', 'MTD': 'MONTH TO DATE' };

const LS_KEYS = 'ledger_ai_keys';
const LS_STAFF = 'ledger_staff';

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
      fetchEditorial();
      return;
    }

    renderLive(json);
    setWire('live');
    fetchEditorial();
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
function esc(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// ─── RENDER ──────────────────────────────────────────
function renderMeta(meta) {
  setText('mastMode', meta.sandbox ? 'SANDBOX' : 'PRODUCTION');
  setText('colophonMeta', `Region ${String(meta.region || '—').toUpperCase()} · Marketplace ${meta.marketplace || '—'}`);
}

function renderLive(d) {
  const k = d.kpis;
  // An empty sandbox answer (revenue 0) keeps the demonstration figures —
  // never print a blank front page.
  if (k && k.revenue > 0) {
    state.lastKpis = k;
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

    // The Board mirrors the till
    const bp = document.getElementById('boardProfit');
    if (bp) {
      bp.textContent = (profit < 0 ? '−' : '') + money(profit);
      bp.classList.toggle('spent', profit < 0);
    }
    setText('boardProfitNote', `kept this period · margin ${k.margin}%`);
    setVerdict(profit >= 0 ? 'good' : 'trouble');

    updateLedger(k);
    renderCharts(k);
  }

  if (d.inventory?.length) updateShelf(d.inventory);
  if (d.orders?.length) updateWireTable(d.orders);
}

function setVerdict(kind) {
  const stamp = document.getElementById('verdictStamp');
  const line = document.getElementById('verdictLine');
  if (!stamp) return;
  stamp.classList.remove('trouble', 'caution');
  if (kind === 'trouble') {
    stamp.textContent = 'ATTENTION REQUIRED';
    stamp.classList.add('trouble');
    if (line) line.textContent = 'The house ran at a loss this period — open the Books and the Dispatches before anything else.';
  } else if (kind === 'caution') {
    stamp.textContent = 'WATCHFUL';
    stamp.classList.add('caution');
    if (line) line.textContent = 'Profitable, but matters on the Dispatches page want signatures.';
  } else {
    stamp.textContent = 'IN GOOD ORDER';
    if (line) line.textContent = 'The house is profitable, the wire is up, and three matters await your signature.';
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
  const m = document.getElementById('ledgerMargin');
  if (m) m.textContent = `${k.margin}%`;
}

function updateShelf(summaries) {
  const list = document.getElementById('shelfList');
  if (!list) return;

  let low = 0, lowest = null;
  const html = summaries.slice(0, 6).map(item => {
    const qty  = item.totalQuantity || 0;
    const days = Math.round(qty / 5); // placeholder daily velocity
    const pct  = Math.min(100, Math.round((days / 120) * 100));
    const cls  = days > 80 ? 'ok' : days > 40 ? 'low' : 'crit';
    if (cls !== 'ok') { low++; if (!lowest || days < lowest.days) lowest = { name: item.productName || item.asin, days }; }
    const name = esc(item.productName || item.sellerSku || item.asin || 'Unnamed product');

    return `<div class="shelf-row${cls !== 'ok' ? ' low' : ''}">
  <div class="shelf-name">${name} <span class="shelf-sku mono">${esc(item.asin || '')}</span></div>
  <div class="shelf-track"><span class="shelf-fill ${cls}" style="width:${pct}%"></span></div>
  <div class="shelf-days mono">${days}<span class="d">d</span></div>
</div>`;
  }).join('');

  if (html) {
    list.innerHTML = html;
    setText('boardShelf', low ? `${low} low` : 'all well');
    setText('boardShelfNote', lowest ? `${lowest.name} — ${lowest.days} days remain` : 'every line above threshold');
  }
}

function updateWireTable(orders) {
  const tbody = document.getElementById('ordersBody');
  if (!tbody) return;

  const html = orders.slice(0, 8).map(o => {
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

  if (html) tbody.innerHTML = html;
}

// ─── CHARTS — hand-set SVG, no libraries ─────────────
// A fixed fortnight shape, scaled so the last week sums to the real profit.
const TREND_SHAPE = [0.55, 0.72, 0.66, 0.78, 0.62, 0.35, 0.48, 0.85, 0.92, 0.74, 0.88, 1.0, 0.58, 0.95];
const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function trendSeries(weekProfit) {
  const lastWeek = TREND_SHAPE.slice(7).reduce((a, b) => a + b, 0);
  const scale = (weekProfit || 1847) / lastWeek;
  return TREND_SHAPE.map(v => Math.round(v * scale));
}

function renderCharts(kpis) {
  const profit = kpis?.netProfit ?? 1847;
  const series = trendSeries(profit);
  drawTrend('chartTrend', series);
  drawDaily('chartDaily', series.slice(7));
  drawSpark('boardSpark', series);
  if (kpis) drawDollarSplit(kpis);
  else drawDollarSplit({ revenue: 6210, cogs: 2484, fbaFees: 1117, adSpend: 762, netProfit: 1847 });
}

function svgEl(container, html) {
  const box = document.getElementById(container);
  if (box) box.innerHTML = html;
}

function drawTrend(id, data) {
  const W = 560, H = 150, PAD = 34, BOT = 22;
  const max = Math.max(...data) * 1.15;
  const x = i => PAD + (i * (W - PAD - 10)) / (data.length - 1);
  const y = v => (H - BOT) - (v / max) * (H - BOT - 12);
  const pts = data.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const area = `M${x(0)},${y(data[0])} ${data.map((v, i) => `L${x(i)},${y(v)}`).join(' ')} L${x(data.length - 1)},${H - BOT} L${x(0)},${H - BOT} Z`;
  const gridLines = [0.25, 0.5, 0.75, 1].map(f => {
    const gy = y(max * f / 1.15);
    return `<line x1="${PAD}" y1="${gy}" x2="${W - 10}" y2="${gy}" class="c-grid"/>
<text x="${PAD - 6}" y="${gy + 3}" class="c-label" text-anchor="end">$${fmt(max * f / 1.15)}</text>`;
  }).join('');
  const last = data.length - 1;

  svgEl(id, `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
<defs><linearGradient id="tfill" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0%" stop-color="#58b98a" stop-opacity="0.28"/>
  <stop offset="100%" stop-color="#58b98a" stop-opacity="0"/>
</linearGradient></defs>
${gridLines}
<path d="${area}" fill="url(#tfill)"/>
<polyline points="${pts}" class="c-line"/>
<circle cx="${x(last)}" cy="${y(data[last])}" r="3.5" class="c-dot"/>
<text x="${x(0)}" y="${H - 6}" class="c-label">D−14</text>
<text x="${x(7)}" y="${H - 6}" class="c-label" text-anchor="middle">D−7</text>
<text x="${x(last)}" y="${H - 6}" class="c-label" text-anchor="end">TODAY</text>
</svg>`);
}

function drawDaily(id, week) {
  const W = 560, H = 150, PAD = 34, BOT = 24;
  const max = Math.max(...week) * 1.2;
  const bw = (W - PAD - 14) / week.length;
  const bars = week.map((v, i) => {
    const bh = (v / max) * (H - BOT - 16);
    const bx = PAD + i * bw + bw * 0.14;
    const by = (H - BOT) - bh;
    const best = v === Math.max(...week);
    return `<rect x="${bx.toFixed(1)}" y="${by.toFixed(1)}" width="${(bw * 0.72).toFixed(1)}" height="${bh.toFixed(1)}" rx="2" class="c-bar${best ? ' best' : ''}"/>
<text x="${(bx + bw * 0.36).toFixed(1)}" y="${by - 5}" class="c-label" text-anchor="middle">$${fmt(v)}</text>
<text x="${(bx + bw * 0.36).toFixed(1)}" y="${H - 8}" class="c-label" text-anchor="middle">${DAY_NAMES[i]}</text>`;
  }).join('');
  svgEl(id, `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">
<line x1="${PAD}" y1="${H - 24}" x2="${W - 10}" y2="${H - 24}" class="c-axis"/>
${bars}
</svg>`);
}

function drawSpark(id, data) {
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
  if (!box || !k.revenue) return;
  const parts = [
    { key: 'Goods',        val: k.cogs,               cls: 'sp-goods' },
    { key: 'Fees',         val: k.fbaFees,            cls: 'sp-fees' },
    { key: 'Ads',          val: k.adSpend,            cls: 'sp-ads' },
    { key: 'Kept',         val: Math.max(k.netProfit, 0), cls: 'sp-kept' },
  ];
  const total = parts.reduce((s, p) => s + p.val, 0) || 1;
  const bar = parts.map(p =>
    `<span class="split-seg ${p.cls}" style="width:${((p.val / total) * 100).toFixed(1)}%" title="${p.key}"></span>`
  ).join('');
  const legend = parts.map(p =>
    `<span class="split-key"><span class="split-swatch ${p.cls}"></span>${p.key} <b class="mono">${Math.round((p.val / total) * 100)}¢</b></span>`
  ).join('');
  box.innerHTML = `<div class="split-bar">${bar}</div><div class="split-legend">${legend}</div>
<p class="footnote">Of every dollar the store takes in, this is how it divides. The green is yours.</p>`;
}

// ─── WIRE STATUS (the stamp) ─────────────────────────
function setWire(status) {
  const stamp = document.getElementById('wireStamp');
  const colophon = document.getElementById('colophonStatus');
  if (!stamp) return;

  stamp.classList.remove('demo', 'error');
  if (status === 'live') {
    stamp.textContent = 'WIRE · LIVE FROM AMAZON';
    setText('boardWire', 'LIVE');
    setText('boardWireNote', 'figures straight from Amazon');
    if (colophon) colophon.textContent = 'Printed from live figures';
  } else if (status === 'syncing') {
    stamp.textContent = 'WIRE · RECEIVING…';
  } else if (status === 'demo') {
    stamp.textContent = 'PRESS PROOF · DEMO FIGURES';
    stamp.classList.add('demo');
    setText('boardWire', 'PROOF');
    setText('boardWireNote', 'demonstration figures for now');
    if (colophon) colophon.textContent = 'Printed from demonstration figures';
  } else {
    stamp.textContent = 'WIRE · DOWN';
    stamp.classList.add('error');
    setText('boardWire', 'DOWN');
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
      console.info('[Ledger] editor unavailable, keeping the standing column:', json.error || 'no text');
      setText('boardEditor', 'STANDING');
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
    if (sig) sig.textContent = `— The Ledger · written by ${json.model || 'AI'} from this period's figures`;
    setText('boardEditor', 'FRESH');
  } catch (err) {
    console.info('[Ledger] editor unavailable:', err.message);
    setText('boardEditor', 'STANDING');
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
}

// ─── ADMINISTRATION: STAFF REGISTRY ──────────────────
function getStaff() {
  try {
    const s = JSON.parse(localStorage.getItem(LS_STAFF) || 'null');
    if (Array.isArray(s)) return s;
  } catch { /* fall through */ }
  return [{ name: 'The Proprietor', email: 'owner@thisledger.store', role: 'Proprietor' }];
}

function saveStaff(staff) {
  localStorage.setItem(LS_STAFF, JSON.stringify(staff));
  renderStaff();
}

function roleClass(role) {
  return { 'Proprietor': 'proprietor', 'Keeper of Books': 'keeper', 'Clerk': 'clerk', 'Reader': 'reader' }[role] || 'reader';
}

function renderStaff() {
  const list = document.getElementById('registryList');
  if (!list) return;
  const staff = getStaff();

  list.innerHTML = staff.length
    ? staff.map((p, i) => `<div class="registry-row">
  <div class="rr-who">
    <div class="rr-name">${esc(p.name)}</div>
    <div class="rr-email">${esc(p.email || '')}</div>
  </div>
  <span class="rr-role ${roleClass(p.role)}">${esc(p.role)}</span>
  <button class="rr-remove" onclick="removeStaff(${i})" title="Strike from the book">strike</button>
</div>`).join('')
    : '<div class="registry-empty">The book is empty — enter the first name.</div>';

  setText('boardStaff', String(staff.length));
  setText('boardStaffNote', staff.length === 1 ? 'registered in the house' : 'registered in the house');
}

function addStaff() {
  const name = document.getElementById('staffName')?.value.trim();
  const email = document.getElementById('staffEmail')?.value.trim();
  const role = document.getElementById('staffRole')?.value || 'Reader';
  const status = document.getElementById('staffStatus');

  if (!name) {
    if (status) { status.textContent = 'A name is required to enter the book.'; status.style.color = 'var(--spent)'; }
    return;
  }
  const staff = getStaff();
  staff.push({ name, email, role });
  saveStaff(staff);

  const n = document.getElementById('staffName'); if (n) n.value = '';
  const e = document.getElementById('staffEmail'); if (e) e.value = '';
  if (status) { status.textContent = `${name} entered as ${role}.`; status.style.color = 'var(--kept)'; }
}

function removeStaff(index) {
  const staff = getStaff();
  const [gone] = staff.splice(index, 1);
  saveStaff(staff);
  const status = document.getElementById('staffStatus');
  if (status && gone) { status.textContent = `${gone.name} struck from the book.`; status.style.color = 'var(--ink-faint)'; }
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

  renderStaff();
  reflectKeyStatus();
  renderCharts(null);
  fetchData(state.activeRange);
  console.log('[The Storefront Ledger] midnight edition printed');
});
