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

    const [ordersRes, inventoryRes] = await Promise.all([
      spFetchSafe(token, '/orders/v0/orders', {
        MarketplaceIds: MARKETPLACE,
        CreatedAfter: createdAfter,
      }),
      spFetchSafe(token, '/fba/inventory/v1/summaries', {
        details: 'true',
        granularityType: 'Marketplace',
        granularityId: MARKETPLACE,
        marketplaceIds: MARKETPLACE,
      }),
    ]);

    const orders = ordersRes?.payload?.Orders || [];
    const inventory = inventoryRes?.payload?.inventorySummaries || [];

    // Aggregate revenue and units from orders
    const revenue = orders.reduce((s, o) => s + parseFloat(o.OrderTotal?.Amount || 0), 0);
    const units = orders.reduce(
      (s, o) => s + (o.NumberOfItemsShipped || 0) + (o.NumberOfItemsUnshipped || 0),
      0
    );

    // Fee/COGS estimates until the Finances API is wired in production
    const fbaFees = revenue * 0.11;
    const cogs = revenue * 0.4;
    const adSpend = revenue * 0.12;
    const netProfit = revenue - cogs - fbaFees - adSpend;
    const margin = revenue > 0 ? +((netProfit / revenue) * 100).toFixed(1) : 0;

    // Report which endpoints actually returned so the UI can tell live vs empty
    const sources = {
      orders: !!ordersRes,
      inventory: !!inventoryRes,
    };

    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({
        success: true,
        range,
        meta,
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
