// FBA Store Command — SP-API Data Aggregator
// Runs server-side so credentials never touch the browser

'use strict';

const LWA_TOKEN_URL = 'https://api.amazon.com/auth/o2/token';

// Region + marketplace come from Netlify env vars so the same code serves
// NA/EU/FE accounts and can flip sandbox → production without a code change.
const REGION = (process.env.SP_API_REGION || 'na').trim().toLowerCase();
const SANDBOX = (process.env.SP_API_SANDBOX || 'true').trim().toLowerCase() !== 'false';
const MARKETPLACE = (process.env.SP_API_MARKETPLACE_ID || 'ATVPDKIKX0DER').trim();

function spBase() {
  const host = { na: 'sellingpartnerapi-na', eu: 'sellingpartnerapi-eu', fe: 'sellingpartnerapi-fe' }[REGION]
    || 'sellingpartnerapi-na';
  return `https://${SANDBOX ? 'sandbox.' : ''}${host}.amazon.com`;
}

async function getLWAToken() {
  const clientId = (process.env.SP_API_CLIENT_ID || '').trim();
  const clientSecret = (process.env.SP_API_CLIENT_SECRET || '').trim();
  const refreshToken = (process.env.SP_API_REFRESH_TOKEN || '').trim();

  console.log('[LWA] client_id present:', !!clientId, 'length:', clientId.length);
  console.log('[LWA] region:', REGION, 'sandbox:', SANDBOX, 'marketplace:', MARKETPLACE);

  const body = new URLSearchParams({
    grant_type: 'refresh_token',
    refresh_token: refreshToken,
    client_id: clientId,
    client_secret: clientSecret,
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
    headers: {
      'x-amz-access-token': token,
      'Content-Type': 'application/json',
    },
  });

  const json = await res.json();
  if (!res.ok) throw new Error(`SP-API ${path} ${res.status}: ${JSON.stringify(json)}`);
  return json;
}

// ── Real Amazon fees out of the Finances API payload ────────────────
// Sums every negative fee/charge across shipment and service events.
function sumAmazonFees(financeRes) {
  const ev = financeRes?.payload?.FinancialEvents;
  if (!ev) return null;
  let fees = 0;
  const addList = (list) => (list || []).forEach(f => {
    const amt = parseFloat(f?.FeeAmount?.CurrencyAmount ?? f?.ChargeAmount?.CurrencyAmount ?? 0);
    if (amt < 0) fees += Math.abs(amt);
  });
  (ev.ShipmentEventList || []).forEach(s => {
    (s.ShipmentItemList || []).forEach(it => { addList(it.ItemFeeList); });
    addList(s.ShipmentFeeList);
  });
  (ev.ServiceFeeEventList || []).forEach(s => addList(s.FeeList));
  return Math.round(fees);
}

// ── Supabase history (best-effort persistence of daily snapshots) ────
const SB_URL = (process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
const SB_KEY = (process.env.SUPABASE_SERVICE_KEY || '').trim();

async function sbUpsertHistory(row) {
  if (!SB_URL || !SB_KEY) return;
  await fetch(`${SB_URL}/rest/v1/ledger_history?on_conflict=day`, {
    method: 'POST',
    headers: {
      apikey: SB_KEY,
      Authorization: `Bearer ${SB_KEY}`,
      'Content-Type': 'application/json',
      Prefer: 'resolution=merge-duplicates,return=minimal',
    },
    body: JSON.stringify(row),
  });
}

async function sbReadHistory(days) {
  if (!SB_URL || !SB_KEY) return [];
  const res = await fetch(`${SB_URL}/rest/v1/ledger_history?select=day,revenue,net,units,orders,margin&order=day.asc&limit=${days}`, {
    headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` },
  });
  if (!res.ok) return [];
  return res.json();
}

// Resolve a fetch but never throw — records the outcome in `diag` so the
// dashboard can show exactly which endpoint answered and why one didn't.
async function spFetchSafe(token, path, params, diag, label) {
  try {
    const res = await spFetch(token, path, params);
    diag.push({ endpoint: label, ok: true, note: 'answered' });
    return res;
  } catch (err) {
    // Pull the HTTP status and Amazon's own reason out of the thrown message.
    const m = /\s(\d{3}):/.exec(err.message);
    const status = m ? Number(m[1]) : null;
    let reason = err.message;
    if (status === 403) reason = 'Access denied — this data role is not approved for the app (Seller Central → Apps → roles).';
    else if (status === 404) reason = 'Not found — endpoint or resource unavailable for this account/region.';
    else if (status === 400) reason = 'Bad request — often a marketplace/region mismatch.';
    else if (status === 429) reason = 'Rate limited — Amazon is throttling; will retry next refresh.';
    diag.push({ endpoint: label, ok: false, status, note: reason });
    console.warn('[sp-api-data] endpoint failed:', path, '-', err.message);
    return null;
  }
}

exports.handler = async (event) => {
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  };

  const meta = { region: REGION, sandbox: SANDBOX, marketplace: MARKETPLACE };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  try {
    const range = event.queryStringParameters?.range || '7D';

    // Auth can fail (bad/expired creds). Never let it 500 the whole request —
    // return success:false with a reason so the UI can show a clean status.
    let token;
    try {
      token = await getLWAToken();
    } catch (authErr) {
      console.error('[sp-api-data] auth failed:', authErr.message);
      return {
        statusCode: 200,
        headers: cors,
        body: JSON.stringify({
          success: false,
          stage: 'auth',
          error: authErr.message,
          meta,
          kpis: null,
        }),
      };
    }

    // Sandbox only answers the magic TEST_CASE_200 value; production needs a
    // real ISO timestamp for the selected range.
    const days = range === '30D' ? 30 : range === 'MTD' ? new Date().getDate() : 7;
    const createdAfter = SANDBOX
      ? 'TEST_CASE_200'
      : new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();

    const diag = [{ endpoint: 'Login with Amazon (auth)', ok: true, note: 'token obtained' }];
    const [ordersRes, inventoryRes, financeRes] = await Promise.all([
      spFetchSafe(token, '/orders/v0/orders', {
        MarketplaceIds: MARKETPLACE,
        CreatedAfter: createdAfter,
      }, diag, 'Orders'),
      spFetchSafe(token, '/fba/inventory/v1/summaries', {
        details: 'true',
        granularityType: 'Marketplace',
        granularityId: MARKETPLACE,
        marketplaceIds: MARKETPLACE,
      }, diag, 'FBA Inventory'),
      SANDBOX ? Promise.resolve(null) : spFetchSafe(token, '/finances/v0/financialEvents', {
        PostedAfter: createdAfter,
        MaxResultsPerPage: 100,
      }, diag, 'Finances (fees)'),
    ]);

    const orders = ordersRes?.payload?.Orders || [];
    const inventory = inventoryRes?.payload?.inventorySummaries || [];

    // Aggregate revenue and units from orders
    const revenue = orders.reduce((s, o) => s + parseFloat(o.OrderTotal?.Amount || 0), 0);
    const units = orders.reduce(
      (s, o) => s + (o.NumberOfItemsShipped || 0) + (o.NumberOfItemsUnshipped || 0),
      0
    );

    // Real per-day revenue/orders across ALL fetched orders, for the charts
    const byDay = {};
    orders.forEach(o => {
      const day = (o.PurchaseDate || '').slice(0, 10);
      if (!day) return;
      byDay[day] = byDay[day] || { date: day, revenue: 0, orders: 0 };
      byDay[day].revenue += parseFloat(o.OrderTotal?.Amount || 0);
      byDay[day].orders += 1;
    });
    const daily = Object.values(byDay).sort((a, b) => a.date.localeCompare(b.date));

    // Real Amazon fees from the Finances API when the role is approved;
    // otherwise fall back to an estimate and flag it.
    const realFees = financeRes ? sumAmazonFees(financeRes) : null;
    const feesReal = realFees !== null && realFees > 0;
    const fbaFees = feesReal ? realFees : revenue * 0.11;

    // COGS is the seller's own purchase cost — Amazon never knows it, so it
    // stays an estimate until the owner enters real costs. Ad spend needs the
    // Advertising API. Both are clearly tagged 'est.' in the UI.
    const cogs = revenue * 0.4;
    const adSpend = revenue * 0.12;
    const netProfit = revenue - cogs - fbaFees - adSpend;
    const margin = revenue > 0 ? +((netProfit / revenue) * 100).toFixed(1) : 0;

    const sources = { orders: !!ordersRes, inventory: !!inventoryRes, finances: !!financeRes };

    // Persist today's snapshot and read back real history (best-effort — a
    // missing table or slow DB never breaks the dashboard).
    let history = [];
    try {
      const today = new Date().toISOString().slice(0, 10);
      await sbUpsertHistory({ day: today, revenue: Math.round(revenue), net: Math.round(netProfit), units, orders: orders.length, margin });
      history = await sbReadHistory(30);
    } catch (histErr) {
      console.warn('[sp-api-data] history unavailable:', histErr.message);
    }

    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({
        success: true,
        range,
        meta,
        sources,
        feesReal,
        kpis: {
          revenue: Math.round(revenue),
          netProfit: Math.round(netProfit),
          margin,
          units,
          fbaFees: Math.round(fbaFees),
          cogs: Math.round(cogs),
          adSpend: Math.round(adSpend),
        },
        orders: orders.slice(0, 10),
        totalOrders: orders.length,
        daily,
        history,
        inventory,
        diagnostics: diag,
        syncedAt: new Date().toISOString(),
      }),
    };
  } catch (err) {
    console.error('[sp-api-data]', err.message);
    return {
      statusCode: 500,
      headers: cors,
      body: JSON.stringify({ success: false, error: err.message, meta }),
    };
  }
};
