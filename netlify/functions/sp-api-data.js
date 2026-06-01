// FBA Intelligence Terminal — SP-API Data Aggregator
// Runs server-side so credentials never touch the browser

'use strict';

const LWA_TOKEN_URL = 'https://api.amazon.com/auth/o2/token';
const MARKETPLACE_US = 'ATVPDKIKX0DER';

function spBase() {
  return 'https://sandbox.sellingpartnerapi-na.amazon.com';
}

async function getLWAToken() {
  const clientId = (process.env.SP_API_CLIENT_ID || '').trim();
  const clientSecret = (process.env.SP_API_CLIENT_SECRET || '').trim();
  const refreshToken = (process.env.SP_API_REFRESH_TOKEN || '').trim();

  console.log('[LWA] client_id present:', !!clientId, 'length:', clientId.length);
  console.log('[LWA] client_secret present:', !!clientSecret, 'length:', clientSecret.length);
  console.log('[LWA] refresh_token present:', !!refreshToken, 'length:', refreshToken.length);
  console.log('[LWA] client_id starts with:', clientId.substring(0, 30));

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

// Resolve a fetch but never throw — returns null on failure so one bad
// endpoint doesn't take down the whole dashboard.
async function spFetchSafe(token, path, params) {
  try {
    return await spFetch(token, path, params);
  } catch (err) {
    console.warn('[sp-api-data] endpoint failed:', path, '-', err.message);
    return null;
  }
}

exports.handler = async (event) => {
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  try {
    const range = event.queryStringParameters?.range || '7D';

    // The SP-API SANDBOX only returns data for Amazon's documented "magic"
    // test values — real timestamps are rejected with "Could not match input
    // arguments". These TEST_CASE_200 values trigger the canned 200 responses.
    const token = await getLWAToken();

    const [ordersRes, inventoryRes, financeRes] = await Promise.all([
      spFetchSafe(token, '/orders/v0/orders', {
        MarketplaceIds: MARKETPLACE_US,
        CreatedAfter: 'TEST_CASE_200',
      }),
      spFetchSafe(token, '/fba/inventory/v1/summaries', {
        details: 'true',
        granularityType: 'Marketplace',
        granularityId: MARKETPLACE_US,
        marketplaceIds: MARKETPLACE_US,
      }),
      spFetchSafe(token, '/finances/v0/financialEventGroups', {
        MaxResultsPerPage: 10,
        FinancialEventGroupStartedBefore: 'TEST_CASE_200',
      }),
    ]);

    const orders = ordersRes?.payload?.Orders || [];
    const inventory = inventoryRes?.payload?.inventorySummaries || [];
    const financeGroups = financeRes?.payload?.FinancialEventGroupList || [];

    // Aggregate revenue and units from orders
    const revenue = orders.reduce((s, o) => s + parseFloat(o.OrderTotal?.Amount || 0), 0);
    const units = orders.reduce(
      (s, o) => s + (o.NumberOfItemsShipped || 0) + (o.NumberOfItemsUnshipped || 0),
      0
    );

    // Sum fees from finance event groups
    const fbaFees = financeGroups.reduce((s, g) => {
      const amt = parseFloat(g.ConvertedTotal?.Amount || 0);
      return s + (amt < 0 ? Math.abs(amt) : 0);
    }, 0);

    // WAC COGS estimate (40% of revenue) — replace with real COGS report when available
    const cogs = revenue * 0.4;
    const adSpend = revenue * 0.12;
    const netProfit = revenue - cogs - fbaFees - adSpend;
    const margin = revenue > 0 ? +((netProfit / revenue) * 100).toFixed(1) : 0;

    // Report which endpoints actually returned so the UI can tell live vs empty
    const sources = {
      orders: !!ordersRes,
      inventory: !!inventoryRes,
      finances: !!financeRes,
    };

    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({
        success: true,
        range,
        sources,
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
        inventory,
        financeGroups: financeGroups.slice(0, 5),
        syncedAt: new Date().toISOString(),
      }),
    };
  } catch (err) {
    console.error('[sp-api-data]', err.message);
    return {
      statusCode: 500,
      headers: cors,
      body: JSON.stringify({ success: false, error: err.message }),
    };
  }
};
