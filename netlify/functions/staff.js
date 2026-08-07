// The Storefront Ledger — Staff & Sessions (Supabase-backed)
// Real accounts: passcodes hashed with scrypt, sessions server-side.
// Uses the service key from Netlify env — never exposed to the browser.

'use strict';

const crypto = require('crypto');

const SB_URL = (process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
const SB_KEY = (process.env.SUPABASE_SERVICE_KEY || '').trim();

const SESSION_DAYS = 7;

function sbHeaders() {
  return {
    'apikey': SB_KEY,
    'Authorization': `Bearer ${SB_KEY}`,
    'Content-Type': 'application/json',
    'Prefer': 'return=representation',
  };
}

async function sb(method, path, body) {
  const res = await fetch(`${SB_URL}/rest/v1/${path}`, {
    method,
    headers: sbHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const json = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(json?.message || `Supabase ${res.status}`);
  return json;
}

function hashPass(pass) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(pass, salt, 64).toString('hex');
  return `${salt}:${hash}`;
}

function verifyPass(pass, stored) {
  const [salt, hash] = String(stored).split(':');
  if (!salt || !hash) return false;
  const check = crypto.scryptSync(pass, salt, 64).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), Buffer.from(check, 'hex'));
}

async function createSession(staffId) {
  const rows = await sb('POST', 'ledger_sessions', { staff_id: staffId });
  return rows[0].token;
}

async function requireSession(token) {
  if (!token) throw new Error('not signed in');
  const rows = await sb('GET',
    `ledger_sessions?token=eq.${encodeURIComponent(token)}&select=token,created_at,ledger_staff(id,name,role)`);
  const s = rows?.[0];
  if (!s || !s.ledger_staff) throw new Error('session expired — sign in again');
  const ageDays = (Date.now() - new Date(s.created_at).getTime()) / 86400000;
  if (ageDays > SESSION_DAYS) {
    await sb('DELETE', `ledger_sessions?token=eq.${encodeURIComponent(token)}`);
    throw new Error('session expired — sign in again');
  }
  return s.ledger_staff;
}

exports.handler = async (event) => {
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
  const reply = (obj) => ({ statusCode: 200, headers: cors, body: JSON.stringify(obj) });

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  if (!SB_URL || !SB_KEY) {
    return reply({ success: false, error: 'backend not configured' });
  }

  let body = {};
  try { body = JSON.parse(event.body || '{}'); } catch { /* empty */ }
  const action = body.action;

  try {
    if (action === 'status') {
      const rows = await sb('GET', 'ledger_staff?select=id&limit=1');
      return reply({ success: true, hasKeeper: rows.length > 0 });
    }

    if (action === 'bootstrap') {
      const { name, pass } = body;
      if (!name || !pass || pass.length < 4) throw new Error('a name and a passcode of at least 4 characters');
      const existing = await sb('GET', 'ledger_staff?select=id&limit=1');
      if (existing.length) throw new Error('the house already has a keeper — sign in instead');
      const rows = await sb('POST', 'ledger_staff', {
        name, email: (body.email || '').toLowerCase(), role: 'Proprietor', pass_hash: hashPass(pass),
      });
      const token = await createSession(rows[0].id);
      return reply({ success: true, token, name: rows[0].name, role: rows[0].role });
    }

    if (action === 'login') {
      const who = String(body.who || '').trim().toLowerCase();
      const pass = body.pass || '';
      if (!who || !pass) throw new Error('name and passcode required');
      const rows = await sb('GET',
        `ledger_staff?or=(name.ilike.${encodeURIComponent(who)},email.eq.${encodeURIComponent(who)})&select=id,name,role,pass_hash`);
      const match = rows.find(r => verifyPass(pass, r.pass_hash));
      if (!match) throw new Error('the book does not recognise that name and passcode');
      const token = await createSession(match.id);
      return reply({ success: true, token, name: match.name, role: match.role });
    }

    if (action === 'signout') {
      if (body.token) await sb('DELETE', `ledger_sessions?token=eq.${encodeURIComponent(body.token)}`);
      return reply({ success: true });
    }

    if (action === 'list') {
      await requireSession(body.token);
      const rows = await sb('GET', 'ledger_staff?select=id,name,email,role,created_at&order=created_at.asc');
      return reply({ success: true, staff: rows });
    }

    if (action === 'add') {
      const me = await requireSession(body.token);
      if (me.role !== 'Proprietor') throw new Error('only the Proprietor may enter names in the book');
      const { name, role, pass } = body;
      if (!name || !pass || pass.length < 4) throw new Error('a name and a passcode of at least 4 characters');
      await sb('POST', 'ledger_staff', {
        name, email: (body.email || '').toLowerCase(), role: role || 'Reader', pass_hash: hashPass(pass),
      });
      return reply({ success: true });
    }

    if (action === 'remove') {
      const me = await requireSession(body.token);
      if (me.role !== 'Proprietor') throw new Error('only the Proprietor may strike names from the book');
      if (body.id === me.id) throw new Error('the keeper cannot strike their own name');
      await sb('DELETE', `ledger_staff?id=eq.${encodeURIComponent(body.id)}`);
      return reply({ success: true });
    }

    throw new Error('unknown action');
  } catch (err) {
    console.warn('[staff]', action, '-', err.message);
    return reply({ success: false, error: err.message });
  }
};
