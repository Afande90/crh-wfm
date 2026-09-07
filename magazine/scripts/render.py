#!/usr/bin/env python3
"""Render the magazine HTML to a print-ready PDF (and audit page overflow)."""
import argparse, json, os, sys
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "build" / "magazine.html"
PDF = ROOT / "AnoKar-Sedan-Guide-Issue-01-2026.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

AUDIT_JS = """
() => {
  const out = [];
  document.querySelectorAll('body > .page').forEach(p => {
    const pr = p.getBoundingClientRect();
    let worst = 0, who = '';
    p.querySelectorAll('*').forEach(el => {
      const r = el.getBoundingClientRect();
      // content must also clear the folio strip at the foot of the page
      const guard = /nextup|meter|verdict|twocol|specs|pricebar|itab|step|pick|brand|cta|toc-row|chart|keyfacts|closing|fromissue|newin|pullquote|checklist|segtable|extremes|legend|index-notes|segcols|chips|sign|strip|facts|coverlines/
        .test(String(el.className)) ? 54 : 0;
      const over = Math.max(r.bottom - (pr.bottom - guard), 0);
      if (over > worst) { worst = over; who = el.className || el.tagName; }
    });
    if (worst > 1) out.push({ pg: p.dataset.pg, over: Math.round(worst), who: String(who).slice(0, 46) });
  });
  return out;
}
"""


def finalize(path: Path):
    """Give the exported file the furniture a published issue should carry:
    document metadata and a bookmark outline covering every section and car."""
    cars = json.loads((ROOT / "build" / "content.json").read_text(encoding="utf-8"))["cars"]
    doc = pymupdf.open(path)
    doc.set_metadata({
        "title": "AnoKar — دليل السيدان تحت 100,000 درهم · العدد 01 · 2026",
        "author": "AnoKar Solutions",
        "subject": "دليل شراء سيدان جديدة في الإمارات تحت 100,000 درهم — 48 سيارة، العدد الأول",
        "keywords": "سيدان, الإمارات, دليل شراء, 2026, AnoKar, sedan buying guide, UAE",
        "creator": "AnoKar editorial desk",
        "producer": "AnoKar magazine build pipeline",
    })
    toc = [
        [1, "الغلاف", 1], [1, "بيانات العدد", 2], [1, "الافتتاحية — كيف بُني هذا الدليل؟", 3],
        [1, "المحتويات", 4], [1, "السوق في صفحة واحدة", 6], [1, "تشريح صفحة السيارة", 8],
        [1, "القسم الأول — ثمانٍ وأربعون سيدان", 9],
    ]
    for i, c in enumerate(cars):
        toc.append([2, f'{c["rank"]:02d} · {c["name_en"]} — {c["name_ar"]}', 10 + i])
    toc += [
        [1, "اختيارات المحرر", 58], [1, "الأفضل في كل شريحة", 59],
        [1, "الفهرس الكامل", 60], [1, "دليل العلامات", 62],
        [1, "قبل أن تشتري", 63], [1, "الغلاف الأخير", 64],
    ]
    doc.set_toc(toc)
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
