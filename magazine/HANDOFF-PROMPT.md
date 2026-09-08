# Handoff brief — AnoKar Issue 01 (paste into ChatGPT / Astra)

Copy everything below the line into the other agent. It assumes the agent can
read the repo, run Python, and search the web.

---

You are taking over a finished-but-improvable Arabic print magazine and pushing it
to a professional print standard. Work to the limit of what you can verify — do not
guess, do not invent facts, and do not hand back anything you have not rendered and
inspected yourself.

## 1. What exists

**Repo:** `Afande90/crh-wfm`, branch `claude/magazine-pdf-creation-y2nxkg`, everything
under `magazine/`.

**Product:** `AnoKar-Issue-01-Battle-of-the-100K.pdf` — a 60-page A4 right-to-left
Arabic car magazine ("معركة المئة ألف"), a buyer's guide to 48 new sedans on sale in
the UAE under AED 100,000.

**Build pipeline** (run in this order; each stage is idempotent):

```
python3 scripts/extract.py    # source PDF  -> build/content.json + assets/img/*.jpg
python3 scripts/build.py      # content.json -> build/magazine.html + build/outline.json
python3 scripts/render.py     # HTML -> PDF via headless Chromium, then metadata + outline
python3 scripts/render.py --no-pdf --shots 7 14 30   # audit only + page PNGs to build/shots/
```

- `scripts/extract.py` — pulls all car records and imagery out of the original source
  PDF (`build/source.pdf`). The source stores Arabic as pre-shaped presentation-form
  glyphs in **visual** order; this script normalises them (NFKC) and rebuilds logical
  order by reversing the sequence of directional runs. **Do not "simplify" this file
  without reading it fully** — the reversal, the tashkeel re-attachment, and the
  `PAREN_FIXES` / `TEXT_FIXES` tables all exist because of real defects in the source.
- `scripts/build.py` — composes all 60 pages as HTML. Page order is computed once from
  constants at the top of `main()` and then asserted; every cross-reference (cover
  lines, contents, "see page N") resolves from those constants.
- `assets/magazine.css` — the entire design system.
- `scripts/copy_ar.py` — all Arabic editorial copy.
- `build/content.json` — 48 car records (41 rated, 7 unrated), each with: `name_ar`,
  `name_en`, `rank`, `price`, `price_updated`, `rating`, `meta` [origin, powertrain,
  segment], 8 `specs`, `strengths`, `caveats`, `verdict`, `fit`, `alternatives`,
  `credit`, `image`.

**Current structure:** cover · contents · editor's letter · methodology · الرادار
(front of book, 2pp) · feature opener + text · data spread · group-test board · five
road-test spreads (dark photo page facing a light analysis page) · head-to-head ·
China report · segment map · "where to start" · buyer's-guide opener · 24 guide pages
(48 cars, two per page) · index (2pp) · brands · glossary · before-you-buy · masthead ·
back cover.

## 2. Defects to fix — these are confirmed, not hypothetical

### 2.1 Bidi break in running Arabic prose (highest priority)

On every road-test analysis page (PDF pages 14, 16, 18, 20, 22) the last paragraph of
`rt_copy()` in `scripts/build.py` embeds a comma-separated list of Latin model names
inside Arabic prose:

```
داخل الميزانية نفسها تقريباً تجد Mazda 3 Sedan، Dongfeng Shine Max، Kia K5. قارنها بالفئة …
```

Rendered, the Unicode bidi algorithm splits that Latin run across the line break and
reorders it against the Arabic. On page 14 the model name "Dongfeng Shine Max" is torn
in half — "Dongfeng Shine" ends one line and "Max" lands at the far left of the next,
next to an unrelated Arabic clause, with the sentence's full stop appearing *before* it.
The reading order is genuinely broken, not just ugly.

Required fix, in order of preference:

1. Stop putting comma-separated Latin lists inside running Arabic sentences. Restructure
   that content as a labelled block (a small "بدائل بالسعر نفسه" table or list) so each
   name occupies its own cell.
2. Wherever a Latin name must sit inside Arabic prose, isolate **each name individually**
   in `<bdi dir="ltr">` with `white-space: nowrap`, and keep the separator (`،`) outside
   the isolate.
3. Then sweep the whole issue for the same class of bug: any Arabic string containing two
   or more Latin runs, or a Latin run adjacent to a number. Candidates already known:
   the source `verdict` strings (several embed a Latin model name, e.g. Camry, Elantra,
   K5, UNI-V, Qin Plus), the `fit` strings, `.say` lines in guide entries, and the
   editor's letter. Every one of these must be checked in the rendered PDF, not in the
   HTML.

### 2.2 Cars are not fully visible / imagery is below print standard

The imagery came out of the source PDF and is the weakest part of the issue:

| Files | Pixels | Effective DPI across a 210 mm page |
|---|---|---|
| 41 | 1473 × 391 | 178 |
| 7 | 1400 × 371 | 169 |
| 1 | 1225 × 391 | 148 |
| 5 | 416 × 266 | 50 |

Two problems follow from that: the aspect ratio is a fixed ~3.77:1 letterbox, so any
layout needing a taller image has to crop the car; and 148–178 dpi is well under the
300 dpi print standard, so the pages are soft when printed. The current build works
around this by running full-page art as a sharp band at the native ratio over a blurred
copy of itself. That is a workaround, not a fix.

**Your task:** source better photography from the web for as many of the 48 cars as you
can, and rebuild the image pipeline around it.

Requirements for every replacement image:
- **Correct car.** Match the exact make, model, generation *and* model year in
  `content.json`. A facelift or a different-market body is a factual error — the
  captions claim the image identifies the car and generation.
- **Full vehicle in frame**, three-quarter front or side, not a cropped detail.
- **At least 2400 px wide**, ideally 3000+. Prefer 16:9 or 3:2 over letterbox so that
  layouts can crop to portrait or square without losing the car.
- **Clean provenance.** Prefer manufacturer press/media rooms and official regional
  newsrooms, which publish press imagery for editorial use. Record for each image, in a
  machine-readable manifest (`assets/img/sources.json`): the car, the source URL, the
  publisher, the date retrieved, and the stated usage terms. If you cannot establish
  usage terms for an image, **do not use it** — keep the existing one and note why.
- **Do not generate car images with an image model.** A synthesised car is a fabricated
  product photo and cannot appear in a buyer's guide.

Then: keep the existing extracted image as an automatic fallback per car, update
`extract.py` (or add `scripts/fetch_images.py`) so the pipeline stays reproducible, and
re-tune the layouts that were built defensively around the letterbox ratio — the
road-test photo pages, the openers, and the cover can all take a real full-bleed crop
once the source images are tall enough. Report a per-car table of what you replaced,
what you kept, and why.

### 2.3 Layout work

Take the layout further, but keep every fix verifiable:

- **Typographic rhythm.** The pages currently sit on ad-hoc vertical spacing. Impose a
  real baseline grid (suggest a 12-column horizontal grid with a ~4 mm baseline) and
  snap headings, body text, captions and figure boxes to it, so facing pages align.
- **Spreads.** Nothing in the issue is currently designed as a true spread. Even-numbered
  pages sit on the right in RTL binding; design at least the feature opener and the
  group-test board as intentional two-page spreads, with the gutter respected (nothing
  important within ~12 mm of the binding edge).
- **Guide pages.** 24 consecutive two-up pages are correct for a buyer's guide but visually
  flat. Introduce controlled variation — a full-width "pick of the segment" entry at each
  segment change, running heads that name the segment and price band, and a thumb index
  on the outer edge.
- **Charts.** The data spread has four charts. Review them for honest encoding (zero
  baselines, no truncated axes), label them directly rather than with legends where
  possible, and make sure every figure has a caption that states what it shows.
- **Colour and contrast.** Verify every text/background pair meets at least 4.5:1; the
  muted greys on the cream stock are the risk.

### 2.4 Correctness sweep

- Every number printed in the issue must trace to `content.json`. Write a checker that
  re-derives each stated aggregate (counts by origin/powertrain/segment, price extremes,
  median, averages, "13 cars between 70–80k", etc.) from the data and fails the build on
  a mismatch. Several of these numbers are currently hard-coded in Arabic prose in
  `scripts/copy_ar.py` — that is the risk you are closing.
- Verify all 48 rank/price orderings and that no car appears with the wrong segment colour.
- Confirm the PDF outline entries all point at the right pages after any repagination.

## 3. Hard constraints — do not violate these

1. **Arabic typography.** `letter-spacing` must be exactly `0` on every Arabic run — the
   script is connected and tracking destroys the letterforms. Tracking is permitted only
   on Latin small-caps labels. Bold is for headlines, not running Arabic text. No italics
   on Arabic. No all-caps Arabic. Right-aligned by default; the whole layout mirrors.
2. **No invented facts.** Prices, specs, ratings, verdicts and dates come from
   `content.json` only. You may write new editorial copy, but every factual claim in it
   must be derivable from the data, and you must be able to point at the field.
3. **Print geometry.** A4 exactly (210 × 297 mm), page count a multiple of 4, the back
   cover last. Add 3 mm bleed and crop marks if you can do it without breaking the
   existing render path.
4. **Fonts.** IBM Plex Sans Arabic (text), Almarai (display), IBM Plex Mono (figures),
   IBM Plex Serif (Latin names) — all OFL, in `assets/fonts/`. If you add a face, it must
   be OFL or equivalently licensed, committed to the repo, and cover Arabic.
5. **No regressions.** `python3 scripts/render.py --no-pdf` must report `OVERFLOW: none`,
   and no glyph may fall back to a substitute font (check with PyMuPDF: no `DejaVu` in
   any span's font name).

## 4. How to verify before you hand anything back

Run all of these and paste the results:

```python
import pymupdf
d = pymupdf.open("AnoKar-Issue-01-Battle-of-the-100K.pdf")
print(len(d), d[0].rect)                       # 60 pages, A4, count % 4 == 0
print({k: v for k, v in d.metadata.items() if k in ("title","author","subject")})
print(len(d.get_toc()))                        # outline present and pointing correctly
bad = [(i+1, s["font"]) for i, p in enumerate(d)
       for b in p.get_text("dict")["blocks"] if b["type"] == 0
       for l in b["lines"] for s in l["spans"] if "DejaVu" in s["font"]]
print("font fallbacks:", len(bad))             # must be 0
```

Then, and this is the part that is usually skipped: **render every one of the 60 pages to
PNG and actually look at them.** `scripts/render.py --no-pdf --shots 1 2 3 …` writes them
to `build/shots/`. Check specifically that

- no Latin word is split across a line break or stranded on the wrong side of Arabic text;
- every car is fully in frame on every page where it appears;
- no text collides with, or sits under, any image or the folio;
- facing pages align on the baseline grid.

## 5. Deliverables

1. The rebuilt PDF, 60+ pages, A4, all checks above passing.
2. `assets/img/sources.json` — provenance for every replacement image.
3. A short report: every defect you fixed, every image you replaced (and every one you
   could not, with the reason), and anything you found that this brief did not mention.
4. Commits on the same branch with clear messages; do not force-push over existing history.

If any instruction here conflicts with what you find in the repo, trust the repo and say so
in the report.
