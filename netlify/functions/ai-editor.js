// The Storefront Ledger — "From the Editor" column
// Written by Gemini (primary) with Groq as understudy — whichever answers first
// gets the byline. House keys live in Netlify env vars; a reader may pass their
// own keys in the request body to write with those instead.

'use strict';

const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
const GROQ_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';

function buildPrompt(figures) {
  return `You are the anonymous editor of "The Storefront Ledger", a small
financial broadsheet that covers exactly one small Amazon FBA business, read only
by its owner. Voice: dry, warm, plain-spoken, quietly witty — like a trusted old
accountant who writes well. Never use hype words, emoji, or bullet points.

Write the weekly "From the Editor" column: exactly 3 short paragraphs (2-3
sentences each). Paragraph 1: the single most important thing in the figures.
Paragraph 2: the main risk or decision this week. Paragraph 3: one concrete,
modest growth move. Refer to money in dollars. Be specific to the numbers given.
If figures are missing or zero, write frankly that the wire brought thin numbers
this week and advise patience and one preparatory action.

This period's figures (JSON): ${JSON.stringify(figures)}

Return ONLY the 3 paragraphs, separated by a blank line. No title, no signature.`;
}

async function askGemini(apiKey, prompt) {
  const res = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-goog-api-key': apiKey,
      },
      body: JSON.stringify({
        contents: [{ parts: [{ text: prompt }] }],
        generationConfig: { temperature: 0.8, maxOutputTokens: 500 },
      }),
    }
  );
  const json = await res.json();
  if (!res.ok) throw new Error(json.error?.message || `Gemini ${res.status}`);
  const text = json.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
  if (!text) throw new Error('Gemini returned no text');
  return { text, model: GEMINI_MODEL };
}

async function askGroq(apiKey, prompt) {
  const res = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.8,
      max_tokens: 500,
    }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error?.message || `Groq ${res.status}`);
  const text = json.choices?.[0]?.message?.content?.trim();
  if (!text) throw new Error('Groq returned no text');
  return { text, model: `groq/${GROQ_MODEL}` };
}

exports.handler = async (event) => {
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  let body = {};
  try {
    body = JSON.parse(event.body || '{}');
  } catch { /* keep empty — the editor can still write a general column */ }

  // A reader's own keys (from the Settings page) outrank the house keys.
  const ownKeys = body.keys || {};
  const geminiKey = (ownKeys.gemini || process.env.GEMINI_API_KEY || '').trim();
  const groqKey = (ownKeys.groq || process.env.GROQ_API_KEY || '').trim();

  if (!geminiKey && !groqKey) {
    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({ success: false, error: 'no AI keys configured' }),
    };
  }

  const figures = { period: body.period, range: body.range, kpis: body.kpis };
  const prompt = buildPrompt(figures);
  const errors = [];

  // Gemini writes the column; Groq fills in when Gemini can't make deadline.
  for (const attempt of [
    geminiKey && (() => askGemini(geminiKey, prompt)),
    groqKey && (() => askGroq(groqKey, prompt)),
  ].filter(Boolean)) {
    try {
      const { text, model } = await attempt();
      const paragraphs = text.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean).slice(0, 3);
      return {
        statusCode: 200,
        headers: cors,
        body: JSON.stringify({ success: true, model, paragraphs }),
      };
    } catch (err) {
      console.warn('[ai-editor] provider failed:', err.message);
      errors.push(err.message);
    }
  }

  return {
    statusCode: 200,
    headers: cors,
    body: JSON.stringify({ success: false, error: errors.join(' | ') }),
  };
};
