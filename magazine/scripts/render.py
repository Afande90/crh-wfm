#!/usr/bin/env python3
"""Render the magazine HTML to a print-ready PDF (and audit page overflow)."""
import argparse, json, os, sys
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "build" / "magazine.html"
PDF = ROOT / "AnoKar-Issue-01-Battle-of-the-100K.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

AUDIT_JS = """
() => {
  // art is meant to bleed; body content must clear the folio strip
  const ART = /bgshot|scrim|strip|shot|photo|ph\b|band|flash|cover|opener|back|lower/;
  const CONTENT = /nextup|meter|verdict|specs|itab|step|pick|brand|cta|toc-row|chart|stats|closing|checklist|gloss|gl-item|say|alt|cols|sign|facts|coverlines|bar|hist|quick|gallery|board|fin|seg|rulebox|item|copy|pull|sidebar|table/;
  const out = [];
  document.querySelectorAll('body > .page').forEach(p => {
    const pr = p.getBoundingClientRect();
    let worst = 0, who = '';
    p.querySelectorAll('*').forEach(el => {
      const cn = String(el.className);
      if (ART.test(cn) || el.closest('.bgshot,.strip,.shot,.photo,.ph,.band,.flash')) return;
      const guard = CONTENT.test(cn) ? 54 : 0;
      const r = el.getBoundingClientRect();
      const over = Math.max(r.bottom - (pr.bottom - guard), 0);
      if (over > worst) { worst = over; who = cn || el.tagName; }
    });
    if (worst > 1) out.push({ pg: p.dataset.pg, over: Math.round(worst), who: String(who).slice(0, 46) });
  });
  return out;
}
"""


def finalize(path: Path):
    """Stamp the exported file with document metadata and the issue's outline."""
    outline = json.loads((ROOT / "build" / "outline.json").read_text(encoding="utf-8"))
    doc = pymupdf.open(path)
    doc.set_metadata({
        "title": "AnoKar — معركة المئة ألف · العدد 01 · سبتمبر 2026",
        "author": "AnoKar Solutions",
        "subject": "دليل شراء سيدان جديدة في الإمارات تحت 100,000 درهم — 48 سيارة، العدد الأول",
        "keywords": "سيدان, الإمارات, دليل شراء, 2026, AnoKar, sedan buying guide, UAE",
        "creator": "AnoKar editorial desk",
        "producer": "AnoKar magazine build pipeline",
    })
    doc.set_toc(outline)
    doc.save(path.with_suffix(".tmp.pdf"), garbage=4, deflate=True)
    doc.close()
    path.with_suffix(".tmp.pdf").replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", nargs="*", type=int, help="page numbers to screenshot")
    ap.add_argument("--outdir", default=str(ROOT / "build" / "shots"))
    ap.add_argument("--no-pdf", action="store_true")
    a = ap.parse_args()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        pg = browser.new_page(viewport={"width": 900, "height": 1300})
        pg.goto(HTML.as_uri())
        pg.wait_for_timeout(1200)
        pg.evaluate("document.fonts.ready")

        bad = pg.evaluate(AUDIT_JS)
        if bad:
            print("OVERFLOW:")
            for b in bad:
                print(f"  page {b['pg']:>3}  +{b['over']}px  <- {b['who']}")
        else:
            print("OVERFLOW: none")

        if a.shots:
            out = Path(a.outdir)
            out.mkdir(parents=True, exist_ok=True)
            for n in a.shots:
                el = pg.query_selector(f'.page[data-pg="{n}"]')
                el.screenshot(path=str(out / f"page{n:02d}.png"))
            print(f"shots -> {out}")

        if not a.no_pdf:
            pg.pdf(path=str(PDF), prefer_css_page_size=True, print_background=True)
            finalize(PDF)
            print(f"pdf -> {PDF}  ({PDF.stat().st_size/1e6:.1f} MB)")
        browser.close()


if __name__ == "__main__":
    main()
