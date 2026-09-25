# Prompt Audit — The Storefront Ledger

_Audit date: 2026-09-25. Proposed changes only; no prompt or code file has been edited._

## Assumptions

- **Scope:** the whole repository. The only text that reaches a model is `buildPrompt()` in `netlify/functions/ai-editor.js` and the two request builders next to it (`askGemini`, `askGroq`). The repo has no `CLAUDE.md`, skill files, rule files, tool definitions, or few-shot blocks.
- **Target models:** the models the code calls: `gemini-2.0-flash` (main, `ai-editor.js:8`) and `llama-3.3-70b-versatile` on Groq (fallback, `ai-editor.js:9`). No migration is in progress.
- **Other providers:** this feature uses **Gemini and Groq** (Groq's OpenAI-compatible endpoint), not Claude. This audit doesn't suggest switching providers. Checks that only apply to Claude were skipped because they don't fit these models: thinking and effort settings, prefill 400 errors, and sampling parameters that error on Claude.
- **Provenance:** every line of the prompt comes from one commit, `f3ef3b1` (2026-08-07). The repo's "no estimates anywhere" rule (`bf092ce`, #17) came later. After it, `netProfit` can be `null` (`app.js:100`), and the prompt doesn't handle that case.

## Summary

| Group | Findings | In diff |
|---|---|---|
| 1 — Prompt text | 4 (1 add, 1 rewrite, 2 flag) | 2 |
| 2 — Skill files | 0 (none exist) | 0 |
| 3 — Tool descriptions | 0 (none exist) | 0 |
| 4 — Request config / architecture | 2 (1 add, 1 flag) | 1 |

The prompt is short, gives good context, and has no dated patterns: no pressure language, no step-by-step scripts, no stale few-shot examples. The findings that matter most:

1. **The prompt doesn't cover the null profit that the no-estimates rule creates.** When profit is unknown, `netProfit` is `null`. The prompt only covers the case where the whole dataset is thin, so it can end up writing an estimated profit, which is exactly what #17 bans everywhere else.
2. **No token accounting.** Neither provider call logs usage, so the column's cost can't be seen, and neither can the effect of any prompt change.
3. **A style ban with no reason attached.** "Never use hype words, emoji, or bullet points" mixes a real layout rule (the column is rendered as `<p>` paragraphs with a drop cap) with a style preference the voice line already covers.

## Findings

### F1 — Null figures are unhandled · Medium · add
- **Location:** `netlify/functions/ai-editor.js:21-22`
- **Evidence:** `If figures are missing or zero, write frankly that the wire brought thin numbers this week…`
- **Pattern:** Step 3 / keep-list #1 and #11: context only the author knows, and re-baselining sometimes adds text.
- **Why:** `kpis.netProfit` is `null` whenever an input isn't real (`app.js:99-100`, added in #17 after this prompt). The prompt treats "missing" as the whole dataset being thin. A single `null` next to a real revenue figure invites the model to work out a profit number, which breaks the Ledger's "profit shown only when every input is real" rule.
- **Action:** rewrite: *"A null figure is not known yet (the Ledger prints only real numbers), so never estimate or derive it; mention the gap if it matters. If figures are mostly missing or zero, …"*

### F2 — A style ban with no stated reason · Medium · rewrite
- **Location:** `netlify/functions/ai-editor.js:15`
- **Evidence:** `Never use hype words, emoji, or bullet points.`
- **Pattern:** 1e (judge each ban separately: keep bans that have a real reason, and reword pure style bans as positive statements).
- **Why:** "No bullets or emoji" is a real layout rule: the output is split into paragraphs and rendered as `<p>` with a drop cap (`app.js:705-712`). The line should say that reason. "Hype words" has no reason given, and the positive voice line just before it ("dry, warm, plain-spoken") already covers it.
- **Action:** rewrite to: *"The column is printed as plain prose paragraphs, so no bullet points, headings, or emoji."*

### F3 — No token accounting · Medium · add
- **Location:** `netlify/functions/ai-editor.js:45`, `:66`
- **Pattern:** Group 4: no token accounting.
- **Why:** Without usage numbers, there's no way to measure the cost of this change or any later one.
- **Action:** add: log `usageMetadata` (Gemini) and `usage` (Groq) to the Netlify function log. Check that these field names appear in real responses before relying on them.

### F4 — Hard 3-paragraph / 2-3-sentence limit · Low · flag
- **Location:** `netlify/functions/ai-editor.js:17-18`
- **Pattern:** 1f (fixed numeric length limits).
- **Why it's kept:** The main argument against numeric caps is that they starve a thinking model's reasoning, and it doesn't apply to these non-thinking models. The "exactly 3" rule is also load-bearing: `slice(0, 3)` at line 125 and the drop-cap layout depend on it. Worth revisiting only if the default model becomes a reasoning model.

### F5 — Paragraph separation relies on the model's formatting · Low · flag
- **Location:** `netlify/functions/ai-editor.js:26` and `:125`
- **Pattern:** 1b (an "output ONLY …" instruction plus parsing code, where the API's structured-output feature could do the job).
- **Why it's only flagged:** The blank-line split works, and no failures have been reported. If the model ever returns a single block or a titled column, both providers' JSON-output modes (for example a JSON array of three strings) would replace the instruction and the parser. This wasn't tested against their APIs here.

### F6 — Default model may be old, and output tokens are sized for a non-thinking model · Low · flag
- **Location:** `netlify/functions/ai-editor.js:8`, `:40`
- **Pattern:** Group 4: `max_tokens` sized for the wrong model.
- **Why it's only flagged:** `gemini-2.0-flash` is an older Gemini generation. Its deprecation status couldn't be checked from this environment (Google's docs site was blocked). If `GEMINI_MODEL` is ever pointed at a thinking-capable Gemini, `maxOutputTokens: 500` may also have to cover thinking tokens. That can cut the column short or return no text, which then silently falls back to Groq. Check Google's deprecations page and resize the limit when the model changes.

## Checked and left alone

- **Role line** (`:12-14`): it's followed by real context (the audience, the business, the voice), so it's fine (keep-list #9).
- **The brief for each paragraph** (`:18-20`): a content spec from the owner, not a script for how to think.
- **`temperature: 0.8`** (`:40`, `:61`): this is only a dated setting on Claude models, where it errors. On Gemini and Llama it's a valid, deliberate choice for creative writing.
- **Model call count:** there's one call site, and it does real judgment work (writing the column), so it isn't an LLM running a deterministic plan.
- **Prompt order:** the figures that change on every request come last, after the stable instructions.

## Proposed diff

One hunk per finding: F2, F1, then F3 as two small hunks. It applies cleanly with `git apply`, and the patched file passes `node --check`.

```diff
--- a/netlify/functions/ai-editor.js
+++ b/netlify/functions/ai-editor.js
@@ -14,3 +14,4 @@
 by its owner. Voice: dry, warm, plain-spoken, quietly witty — like a trusted old
-accountant who writes well. Never use hype words, emoji, or bullet points.
+accountant who writes well. The column is printed as plain prose paragraphs,
+so no bullet points, headings, or emoji.
 
@@ -20,4 +21,6 @@
 modest growth move. Refer to money in dollars. Be specific to the numbers given.
-If figures are missing or zero, write frankly that the wire brought thin numbers
-this week and advise patience and one preparatory action.
+A null figure is not known yet (the Ledger prints only real numbers), so never
+estimate or derive it; mention the gap if it matters. If figures are mostly
+missing or zero, write frankly that the wire brought thin numbers this week and
+advise patience and one preparatory action.
 
@@ -45,2 +48,3 @@
   if (!res.ok) throw new Error(json.error?.message || `Gemini ${res.status}`);
+  console.info('[ai-editor] gemini usage:', JSON.stringify(json.usageMetadata || {}));
   const text = json.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
@@ -66,2 +70,3 @@
   if (!res.ok) throw new Error(json.error?.message || `Groq ${res.status}`);
+  console.info('[ai-editor] groq usage:', JSON.stringify(json.usage || {}));
   const text = json.choices?.[0]?.message?.content?.trim();
```

## Verification before merging

The changes to the prompt text (F1, F2) are guesses until tested. Run **Ask the editor to write again** on a period where `netProfit` is `null` and revenue is above zero, before and after the change. Pass: the column never states a profit figure. F3 is the prerequisite for measuring anything beyond that.
