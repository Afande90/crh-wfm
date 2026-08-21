// The Storefront Ledger — Per-ASIN profitability (Phase 2)
// Real per-product revenue & units from Amazon order items, joined to the
// owner's per-ASIN unit cost (product_costs table) for true gross margin.

'use strict';

const crypto = require('crypto');

const LWA_TOKEN_URL = 'https://api.amazon.com/auth/o2/token';
const REGION = (process.env.SP_API_REGION || 'na').trim().toLowerCase();
const SANDBOX = (process.env.SP_API_SANDBOX || 'true').trim().toLowerCase() !== 'false';
const MARKETPLACE = (process.env.SP_API_MARKETPLACE_ID || 'ATVPDKIKX0DER').trim();
const SB_URL = (process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
const SB_KEY = (process.env.SUPABASE_SERVICE_KEY || '').trim();

function spBase() {
  const host = { na: 'sellingpartnerapi-na', eu: 'sellingpartnerapi-eu', fe: 'sellingpartnerapi-fe' }[REGION] || 'sellingpartnerapi-na';
  return `https://${SANDBOX ? 'sandbox.' : ''}${host}.amazon.com`;
}

async function getLWAToken() {
  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: (process.env.SP_API_REFRESH_TOKEN || '').trim(),
    client_id: (process.env.SP_API_CLIENT_ID || '').trim(),
    client_secret: (process.env.SP_API_CLIENT_SECRET || '').trim(),
  });
  const res = await fetch(LWA_TOKEN_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: body.toString(),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(`LWA error: ${JSON.stringify(json)}`);
  return json.access_token;
}

async function spFetch(token, path, params = {}) {
  const url = new URL(spBase() + path);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString(), {
    headers: { 'x-amz-access-token': token, 'Content-Type': 'application/json' },
  });
  const json = await res.json();
  if (!res.ok) throw new Error(`SP-API ${path} ${res.status}`);
  return json;
}

async function sb(method, path, body) {
  const res = await fetch(`${SB_URL}/rest/v1/${path}`, {
    method,
    headers: {
      apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`,
      'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=representation',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const json = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(json?.message || `Supabase ${res.status}`);
  return json;
}

// Confirm the caller holds a valid session (reuses ledger_sessions).
async function requireProprietor(token) {
  if (!token) throw new Error('not signed in');
  const rows = await sb('GET', `ledger_sessions?token=eq.${encodeURIComponent(token)}&select=ledger_staff(role)`);
  const role = rows?.[0]?.ledger_staff?.role;
  if (role !== 'Proprietor') throw new Error('only the Proprietor may set product costs');
}

exports.handler = async (event) => {
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  const reply = (o) => ({ statusCode: 200, headers: cors, body: JSON.stringify(o) });
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: cors, body: '' };

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { /* empty */ }

  try {
    // Save a per-ASIN unit cost (owner action).
    if (body.action === 'saveCost') {
      await requireProprietor(body.token);
      const asin = String(body.asin || '').trim();
      const unitCost = parseFloat(body.unitCost);
      if (!asin || isNaN(unitCost) || unitCost < 0) throw new Error('a valid ASIN and unit cost are required');
      await sb('POST', 'product_costs', { asin, unit_cost: unitCost, notes: 'entered via dashboard' });
      return reply({ success: true });
    }

    // Default: per-ASIN profitability for the range.
    const range = body.range || '7D';
    const days = range === '30D' ? 30 : range === 'MTD' ? new Date().getDate() : 7;
    const createdAfter = SANDBOX ? 'TEST_CASE_200'
      : new Date(Date.now() - days * 864e5).toISOString();

    const token = await getLWAToken();
    let ordersRes;
    try {
      ordersRes = await spFetch(token, '/orders/v0/orders', { MarketplaceIds: MARKETPLACE, CreatedAfter: createdAfter });
    } catch (e) {
      return reply({ success: false, error: e.message });
    }
    const orders = ordersRes?.payload?.Orders || [];

    // Fetch line items per order (capped for rate limits), aggregate by ASIN.
    const byAsin = {};
    const slice = orders.slice(0, 25);
    for (const o of slice) {
      try {
        const it = await spFetch(token, `/orders/v0/orders/${o.AmazonOrderId}/orderItems`, {});
        (it?.payload?.OrderItems || []).forEach(item => {
          const asin = item.ASIN || 'unknown';
          byAsin[asin] = byAsin[asin] || { asin, title: item.Title || asin, units: 0, revenue: 0 };
          byAsin[asin].units += parseInt(item.QuantityOrdered || 0, 10);
          byAsin[asin].revenue += parseFloat(item.ItemPrice?.Amount || 0);
        });
      } catch { /* skip one bad order, keep going */ }
    }

    // Join the owner's latest per-ASIN unit cost.
    let costs = {};
    try {
      const rows = await sb('GET', 'product_costs?select=asin,unit_cost,effective_date&order=effective_date.desc');
      (rows || []).forEach(r => { if (!(r.asin in costs)) costs[r.asin] = parseFloat(r.unit_cost); });
    } catch { /* table may be empty */ }

    const products = Object.values(byAsin).map(p => {
      const unitCost = costs[p.asin];
      const cogs = unitCost != null ? Math.round(unitCost * p.units * 100) / 100 : null;
      const gross = cogs != null ? Math.round((p.revenue - cogs) * 100) / 100 : null;
      const grossMargin = (gross != null && p.revenue > 0) ? +((gross / p.revenue) * 100).toFixed(1) : null;
      return { ...p, revenue: Math.round(p.revenue * 100) / 100, unitCost: unitCost ?? null, cogs, gross, grossMargin };
    }).sort((a, b) => b.revenue - a.revenue);

    return reply({ success: true, range, products, sandbox: SANDBOX });
  } catch (err) {
    console.error('[product-detail]', err.message);
    return reply({ success: false, error: err.message });
  }
};
