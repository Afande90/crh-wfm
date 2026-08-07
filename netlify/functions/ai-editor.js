// The Storefront Ledger — "From the Editor" column
// Written by Google Gemini (free tier) from the store's real figures.
// Runs server-side so the API key never touches the browser.

'use strict';

const MODEL = process.env.GEMINI_MODEL || 'gemini-2.0-flash';

exports.handler = async (event) => {
  const cors = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  const apiKey = (process.env.GEMINI_API_KEY || '').trim();
  if (!apiKey) {
    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({ success: false, error: 'GEMINI_API_KEY not configured' }),
    };
  }

  let figures = {};
  try {
    figures = JSON.parse(event.body || '{}');
  } catch { /* keep empty — the editor can still write a general column */ }

  const prompt = `You are the anonymous editor of "The Storefront Ledger", a small
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

  try {
    const res = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent?key=${apiKey}`,
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
    if (!res.ok) {
      console.error('[ai-editor] Gemini error:', JSON.stringify(json).slice(0, 300));
      return {
        statusCode: 200,
        headers: cors,
        body: JSON.stringify({ success: false, error: json.error?.message || `Gemini ${res.status}` }),
      };
    }

    const text = json.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
    if (!text) {
      return {
        statusCode: 200,
        headers: cors,
        body: JSON.stringify({ success: false, error: 'empty response' }),
      };
    }

    const paragraphs = text.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean).slice(0, 3);

    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({ success: true, model: MODEL, paragraphs }),
    };
  } catch (err) {
    console.error('[ai-editor]', err.message);
    return {
      statusCode: 200,
      headers: cors,
      body: JSON.stringify({ success: false, error: err.message }),
    };
  }
};
