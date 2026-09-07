# AnoKar — دليل السيدان تحت 100,000 درهم · العدد 01

A 64-page, print-ready A4 magazine built from the source buyer's guide PDF
(`build/source.pdf`). Everything in the issue — 48 car profiles, prices, specs,
verdicts, imagery — is extracted from that source; nothing is invented.

**Output:** `AnoKar-Sedan-Guide-Issue-01-2026.pdf` — 64 pages (a multiple of 4,
so it can be saddle-stitched), A4 (210 × 297 mm), RTL Arabic, embedded fonts,
document outline and metadata.

## Pipeline

```bash
python3 scripts/extract.py    # source PDF  -> build/content.json + assets/img/*.jpg
python3 scripts/build.py      # content.json -> build/magazine.html
python3 scripts/render.py     # magazine.html -> AnoKar-Sedan-Guide-Issue-01-2026.pdf
```

`render.py` also audits every page for content that overflows the trim or runs
into the folio, and can dump page screenshots:

```bash
python3 scripts/render.py --no-pdf --shots 1 10 42     # audit + build/shots/*.png
```

Requirements: `pymupdf`, `pillow`, `playwright` (Chromium at
`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`; change `CHROME` in
`scripts/render.py` for another machine).

## Extraction notes

The source PDF stores Arabic as pre-shaped presentation-form glyphs in **visual**
order. `scripts/extract.py` normalises those back to base letters (NFKC) and then
rebuilds logical order by reversing the sequence of directional runs, keeping the
neutrals that sit *inside* a run in place. That recovers mixed Arabic/Latin lines
("… 180 حصاناً …") correctly. Seven bracketed cells and one double-punctuation
line that no general reordering can resolve are corrected by name in
`PAREN_FIXES` / `TEXT_FIXES`.

## Structure of the issue

| Pages | Section |
|---|---|
| 1 | Cover |
| 2 | Masthead / issue data |
| 3 | Editor's letter — how the guide was built |
| 4–5 | Contents (sections, then all 48 files by segment) |
| 6–7 | The market in one spread — four charts, extremes, segment table |
| 8 | Anatomy of a car page (a real page, shrunk and annotated) |
| 9 | Section opener |
| 10–57 | 48 car profiles, cheapest entry price first |
| 58 | Editor's five picks |
| 59 | Best in each of the four segments |
| 60–61 | Full index |
| 62 | Brand guide |
| 63 | Before you buy — four steps and a checklist |
| 64 | Back cover |

Car pages use three templates: a feature opener for the five cars rated 9.0+, and
two alternating standard layouts (photo high / photo low) so facing pages differ.
Each of the four price segments carries its own accent colour throughout.

## Design system

`assets/magazine.css` holds the whole system: A4 page boxes with alternating
recto/verso gutters, the type scale (Almarai for display, IBM Plex Sans Arabic
for text, IBM Plex Mono for figures, IBM Plex Serif for Latin model names), the
segment palette, and every component. Fonts are in `assets/fonts/` (OFL).

Imagery is the official brand photography carried by the source guide, re-exported
as JPEG.
