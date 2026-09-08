# AnoKar — معركة المئة ألف · العدد 01

A 60-page A4 magazine built from the source buyer's-guide PDF. All content and
imagery come from that source (`build/source.pdf`); the running order, layouts
and editorial framing are the magazine's own — the source's one-page-per-car
template is not used anywhere.

**Output:** `AnoKar-Issue-01-Battle-of-the-100K.pdf` — 60 pages (a multiple of 4
for saddle-stitching), A4, RTL Arabic, embedded fonts, metadata and a 72-entry
outline.

## Running order

Built on standard magazine architecture — a fast front of book, an airy feature
well, then a dense service section at the back.

| Pages | | |
|---|---|---|
| 1 | Cover | full-ratio car band over a blurred backdrop |
| 2 | Contents | four picture leads + section list |
| 3–4 | Editor's letter · methodology | inclusion rules, what the score measures |
| 5–6 | **الرادار** — front of book | eleven numbers, dense grid, one dark panel |
| 7–8 | Feature opener + text | "معركة المئة ألف", copy runs on from the opener |
| 9–10 | The market in numbers | five charts, price/rating scatter |
| 11–12 | Group test opener | the five finalists board, how they were ranked |
| 13–22 | Five road-test spreads | dark photo page + light analysis page each |
| 23–24 | Head to head | Corolla vs Qin Plus, comparison table, verdicts |
| 25–26 | Report | how China rewrote the segment, all 29 listed |
| 27–28 | Segment map · where to start | four segments, four reader profiles |
| 29 | Buyer's guide opener | segment key |
| 30–53 | **Buyer's guide** | 48 cars, two a page, full record each |
| 54–55 | Full index | 48 rows, origin dots |
| 56–58 | Brands · glossary · before you buy | |
| 59–60 | Masthead · back cover | |

Every car keeps its complete record — eight specs, strengths, cautions, verdict,
who it suits, alternatives, image credit — in the buyer's guide. The five rated
9.0+ get a full spread in the feature well as well.

## Pipeline

```bash
python3 scripts/extract.py    # source PDF   -> build/content.json + assets/img/*.jpg
python3 scripts/build.py      # content.json -> build/magazine.html + build/outline.json
python3 scripts/render.py     # magazine.html -> AnoKar-Issue-01-Battle-of-the-100K.pdf
```

`render.py` audits every page for content that overflows the trim or collides
with the folio, and can dump page screenshots:

```bash
python3 scripts/render.py --no-pdf --shots 1 13 30
```

Requirements: `pymupdf`, `pillow`, `playwright` (Chromium at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; change `CHROME` in
`scripts/render.py` elsewhere).

## Extraction notes

The source PDF stores Arabic as pre-shaped presentation-form glyphs in *visual*
order. `scripts/extract.py` normalises them back to base letters (NFKC) and
rebuilds logical order by reversing the sequence of directional runs, leaving the
neutrals *inside* a run in place — which recovers mixed Arabic/Latin lines,
numeric ranges and prices. Wrapped bullets are re-joined; the handful of cells no
general reordering can fix (detached bracket pairs, one stacked-punctuation line)
are corrected by name in `PAREN_FIXES` / `TEXT_FIXES`.

## Design notes

- **Arabic typography.** Letter-spacing is zero on every Arabic run — the script
  is connected and tracking it breaks the letterforms. Tracking is reserved for
  Latin small-caps labels. Bold is used for headlines, not for running text; no
  italics, no all-caps Arabic. Numeric ranges are isolated in `<bdi>` so the bidi
  algorithm cannot reorder them.
- **Imagery.** The press shots are 3.77:1. Cropping one to a full page shows a
  wing mirror, so full-page art uses a sharp band at the image's own ratio over a
  blurred, darkened copy of itself; guide entries run the band full bleed.
- **Grid and colour.** Margins alternate recto/verso for the binding edge. Four
  price segments carry their own accent through tags, scores and rules. Type:
  Almarai for display, IBM Plex Sans Arabic for text, IBM Plex Mono for figures,
  IBM Plex Serif for Latin model names (all OFL, in `assets/fonts/`).
