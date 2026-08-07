// The Storefront Ledger — "From the Editor" column
// Written by Gemini (primary) with Grok as understudy — whichever answers first
// gets the byline. Keys live server-side in Netlify env vars only.

'use strict';

const GEMINI_MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';
const GROK_MODEL = process.env.GROK_MODEL || 'grok-3-mini';

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
    `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${apiKey}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

async function askGrok(apiKey, prompt) {
  const res = await fetch('https://api.x.ai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: GROK_MODEL,
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.8,
      max_tokens: 500,
    }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error?.message || json.error || `Grok ${res.status}`);
  const text = json.choices?.[0]?.message?.content?.trim();
  if (!text) throw new Error('Grok returned no text');
  return { text, model: GROK_MODEL };
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

  const geminiKey = (process.env.GEMINI_API_KEY || '').trim();
  const grokKey = (process.env.GROK_API_KEY || '').trim();

  if (!geminiKey && !grokKey) {
    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({ success: false, error: 'no AI keys configured' }),
    };
  }

  let figures = {};
  try {
    figures = JSON.parse(event.body || '{}');
  } catch { /* keep empty — the editor can still write a general column */ }

  const prompt = buildPrompt(figures);
  const errors = [];

  // Gemini writes the column; Grok fills in when Gemini can't make deadline.
  for (const attempt of [
    geminiKey && (() => askGemini(geminiKey, prompt)),
    grokKey && (() => askGrok(grokKey, prompt)),
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
