#!/usr/bin/env python3
"""Compose the AnoKar sedan guide as a print-ready 64-page magazine (HTML)."""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from copy_ar import ISSUE, COVER_LINES, LETTER, MARKET, ANATOMY, PICKS, GUIDE, BACK

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "build" / "content.json").read_text(encoding="utf-8"))
CARS = DATA["cars"]
OUT = ROOT / "build" / "magazine.html"

SEG_CLASS = {"شريحة الدخول": "entry", "شريحة الاستخدام اليومي": "daily",
             "شريحة العائلية": "family", "شريحة قرب السقف": "cap"}
SEG_COLOR = {"entry": "#B7472A", "daily": "#2C6A4F", "family": "#23486B", "cap": "#7A5B2E"}
ORIGIN_COLOR = {"الصين": "#C3352A", "اليابان": "#23486B", "كوريا": "#2C6A4F", "أوروبا": "#7A5B2E"}

FIRST_CAR_PAGE = 10
PAGE_PICKS, PAGE_BEST, PAGE_INDEX, PAGE_BRANDS, PAGE_GUIDE = 58, 59, 60, 62, 63


def money(s):
    return (s or "—").replace("–", "–")


def low(price):
    m = re.search(r"([\d,]+)", price or "")
    return int(m.group(1).replace(",", "")) if m else 0


def high(price):
    nums = re.findall(r"([\d,]+)", price or "")
    return int(nums[-1].replace(",", "")) if nums else 0


for i, c in enumerate(CARS):
    c["page"] = FIRST_CAR_PAGE + i
    c["seg"] = SEG_CLASS.get(c["meta"][2], "daily")
    c["low"] = low(c["price"])
    c["high"] = high(c["price"])

BY_EN = {c["name_en"]: c for c in CARS}


def find(name_en):
    if name_en in BY_EN:
        return BY_EN[name_en]
    for c in CARS:
        if c["name_en"].startswith(name_en) or name_en.startswith(c["name_en"][:14]):
            return c
    return None


# a numeric range inside an RTL line is re-ordered by the bidi algorithm
# ("31,500 – 43,500" renders reversed), so each one is isolated in its own <bdi>
RANGE = re.compile(r"\d[\d.,]*[A-Za-z]*(?:\s*[–—/-]\s*\d[\d.,]*[A-Za-z]*)+")


def esc(t, isolate=True):
    t = (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if isolate:
        t = RANGE.sub(lambda m: f'<bdi dir="ltr">{m.group(0)}</bdi>', t)
    return t


# ---------------------------------------------------------------- page frame
PAGES = []


def add(html):
    PAGES.append(html)
    return len(PAGES)


def folio(section, n):
    return (f'<div class="folio"><span>{esc(ISSUE["brand"])} · {esc(ISSUE["issue_line"])}</span>'
            f'<span>{esc(section)}</span><span class="no">{n}</span></div>')


def page(cls, inner, section=None, n=None):
    n = n if n is not None else len(PAGES) + 1
    parity = "recto" if n % 2 else "verso"
    f = folio(section, n) if section else ""
    return f'<section class="page {parity} {cls}" data-pg="{n}">{inner}{f}</section>'


def runhead(text):
    return f'<div class="runhead"><span class="dot"></span>{esc(text)}</div>'


# ------------------------------------------------------------------- 1 cover
def cover():
    lines = ""
    for i, (t, p) in enumerate(COVER_LINES, 1):
        lines += (f'<li><span class="ix">{i:02d}</span><span class="tx">{esc(t)}</span>'
                  f'<span class="pg">{esc(p)}</span></li>')
    return page("cover", f'''
    <div class="top">
      <div><div class="wordmark">{ISSUE["brand"]}</div><div class="wm-sub">{ISSUE["brand_sub"]}</div></div>
      <div class="issue"><span>العدد</span><b>01</b><span>2026</span></div>
    </div>
    <div class="masthead-rule"></div>
    <div class="headline"><h1>دليل السيدان<br>تحت <em>100,000</em> درهم</h1>
      <div class="sub">نسخة المشتري الإماراتي · 48 سيدان جديدة داخل سقف واحد</div></div>
    <div class="band"><img src="../assets/img/{DATA["cover_image"]}"></div>
    <div class="flag">اختبار السوق · <bdi dir="ltr">2026</bdi></div>
    <div class="strap">اختبارات السوق كما هي: من أرخص سيدان جديدة في الدولة إلى أقوى سيارة تقف
      عند حاجز الميزانية — 29 صينية، 11 يابانية، ست كورية، واثنتان أوروبيتان.</div>
    <ul class="coverlines">{lines}</ul>
    <div class="stats">
      <div><b>48</b><span>سيدان في العدد</span></div>
      <div><b>31,500</b><span>أدنى دخول · درهم</span></div>
      <div><b>100K</b><span>سقف الميزانية</span></div>
      <div><b>25.08</b><span>قطع البحث · 2026</span></div>
    </div>
    <div class="footline"><span>{ISSUE["site"]}</span><span>ISSUE 01 · UAE EDITION</span></div>''')


# --------------------------------------------------------------- 2 imprint
def imprint():
    return page("imprint", f'''
    {runhead("بيانات العدد")}
    <div class="imprint">
      <h1 style="font-size:27pt;margin:6mm 0 2mm">{esc(ISSUE["title"])}</h1>
      <p class="lede" style="max-width:120mm">{esc(ISSUE["issue_line"])}</p>
      <div class="grid">
        <div class="cell"><dt>عدد السيارات</dt><dd>48</dd><p>{esc(ISSUE["count_line"])}</p></div>
        <div class="cell"><dt>النطاق السعري</dt><dd>31,500 – 99,900</dd>
          <p>درهم إماراتي، سعر الدخول لكل طراز.</p></div>
        <div class="cell"><dt>قطع البحث</dt><dd>25.08.2026</dd>
          <p>كل رقم في هذا العدد يعود إلى هذا التاريخ.</p></div>
        <div class="cell"><dt>الإصدار</dt><dd>1.0</dd><p>{esc(ISSUE["site"])}</p></div>
      </div>
      <div style="margin-top:9mm" class="note">{esc(ISSUE["disclaimer"])}</div>
      <div class="grid" style="margin-top:9mm">
        <div class="cell"><dt>هيئة التحرير</dt><p style="font-size:9pt">بحث وتحرير: فريق أنوكار سوليوشنز<br>
          تصميم وإخراج: قسم النشر<br>مراجعة الأسعار: مصادر الوكلاء داخل الدولة</p></div>
        <div class="cell"><dt>الصور</dt><p style="font-size:9pt">مواد رسمية من العلامات التجارية،
          تُستخدم للتعريف بالسيارة والجيل. حقوق الصور تعود لأصحابها.</p></div>
      </div>
      <div class="grid" style="margin-top:9mm">
        <div class="cell"><dt>كيف نقرأ السعر</dt><p style="font-size:9pt">سعر رسمي من وكيل · سعر سوق
          جديد · سعر استيراد. الثلاثة لا تتساوى، والدليل يفرّق بينها في كل ملف.</p></div>
        <div class="cell"><dt>حقوق النشر</dt><p style="font-size:9pt">© 2026 AnoKar Solutions.
          يجوز الاقتباس مع الإشارة إلى المصدر ورقم العدد.</p></div>
      </div>
    </div>''', "بيانات العدد")


# ------------------------------------------------------------ 3 editor letter
def letter():
    secs = "".join(f'<h3>{esc(t)}</h3><p>{esc(b)}</p>' for t, b in LETTER["sections"])
    strip = ""
    for en, cap in [("Chery Arrizo 5", "أرخص مدخل إلى السوق الجديد"),
                    ("Geely Preface", "صينية تلعب في فئة أعلى"),
                    ("Honda Civic", "آخر ما يشتريه السقف")]:
        c = find(en)
        strip += (f'<figure><img src="../assets/img/{c["image"]}">'
                  f'<figcaption><b>{esc(c["name_en"])}</b><span>{esc(cap)}</span>'
                  f'<u>صفحة {c["page"]}</u></figcaption></figure>')
    return page("letter", f'''
    {runhead(LETTER["kicker"])}
    <div class="letter">
      <h1>{esc(LETTER["title"])}</h1>
      <p class="intro">{esc(LETTER["intro"])}</p>
      <div class="cols">{secs}</div>
      <div class="pullquote">
        <span class="mark">”</span>
        <p>وجود رقم واحد في إعلان لا يجعله سعراً رسمياً.</p>
      </div>
      <div class="newin">
        <div><b>41</b><span>سيارة مُقيَّمة برقم واحد من عشرة</span></div>
        <div><b>7</b><span>إضافات محدَّثة دخلت بلا تقييم</span></div>
        <div><b>4</b><span>شرائح تقسّم السقف إلى قرارات</span></div>
      </div>
      <div class="fromissue">
        <div class="lbl">من هذا العدد</div>
        <div class="strip">{strip}</div>
      </div>
      <div class="sign"><b>{esc(LETTER["sign"])}</b><span>— {esc(ISSUE["site"])}</span></div>
    </div>''', "الافتتاحية")


# --------------------------------------------------------------- 4-5 contents
def toc_row(pg, ar, en, right=""):
    en_html = f'<span class="en">{esc(en)}</span>' if en else ""
    return (f'<div class="toc-row"><span class="p">{pg}</span>'
            f'<span class="t">{esc(ar)}{en_html}</span><span class="r">{esc(right)}</span></div>')


def contents_1():
    feats = []
    for en, cap in [("Toyota Corolla", "اختيار المحرر"), ("BYD Qin Plus DM-i", "أفضل هجين"),
                    ("Chery Arrizo 5", "أرخص جديدة"), ("Honda Civic", "أقوى داخل السقف")]:
        c = find(en)
        feats.append(f'<figure><img src="../assets/img/{c["image"]}">'
                     f'<figcaption><span>{esc(cap)}</span><b>{c["page"]}</b></figcaption></figure>')
    rows = [
        toc_row("02", "بيانات العدد", "", "المصادر وحدود البحث"),
        toc_row("03", "الافتتاحية — كيف بُني هذا الدليل؟", "", "قواعد الإدراج"),
        toc_row("06", "السوق في صفحة واحدة", "", "المنشأ · المنظومة · الأسعار"),
        toc_row("08", "تشريح صفحة السيارة", "", "كيف تقرأ الملفات"),
        toc_row("09", "القسم الأول — ثمانٍ وأربعون سيدان", "", "48 ملفاً"),
        toc_row(str(PAGE_PICKS), "اختيارات المحرر", "", "خمس سيارات أولاً"),
        toc_row(str(PAGE_BEST), "الأفضل في كل شريحة", "", "أربعة قرارات"),
        toc_row(str(PAGE_INDEX), "الفهرس الكامل من الأرخص إلى الأعلى", "", "48 صفاً"),
        toc_row(str(PAGE_BRANDS), "دليل العلامات", "", "25 علامة"),
        toc_row(str(PAGE_GUIDE), "قبل أن تشتري — أربع خطوات", "", "الخلاصة"),
    ]
    return page("toc", f'''
    {runhead("المحتويات")}
    <div class="toc">
      <h1>المحتويات</h1>
      <div class="sub">العدد 01 · دليل السيدان تحت 100,000 درهم</div>
      <div class="toc-feat">{"".join(feats)}</div>
      <div class="toc-head"><span>صفحة</span><span>الباب</span><span>ملاحظة</span></div>
      {"".join(rows)}
      <div class="toc-sec">الملفات مرتبة بحسب سعر الدخول</div>
      <p class="body" style="margin-top:2mm;color:var(--muted);max-width:150mm">
        تبدأ الملفات من الصفحة {FIRST_CAR_PAGE} بأرخص سيدان جديدة في الدولة وتنتهي عند الصفحة
        {FIRST_CAR_PAGE + 47} عند حاجز المئة ألف. القائمة الكاملة بحسب الشريحة في الصفحة المقابلة،
        وجدول الفهرس الكامل في الصفحة {PAGE_INDEX}.</p>
    </div>''', "المحتويات")


def contents_2():
    cols = []
    for label, key in [("شريحة الدخول", "entry"), ("شريحة الاستخدام اليومي", "daily"),
                       ("شريحة العائلية", "family"), ("شريحة قرب السقف", "cap")]:
        items = [c for c in CARS if c["seg"] == key]
        lis = "".join(
            f'<li><span class="en">{esc(c["name_en"])}</span><b>{c["page"]}</b></li>' for c in items)
        cols.append(f'''<div class="segcol">
          <h4 style="border-color:{SEG_COLOR[key]}"><span>{esc(label)}</span>
            <b style="color:{SEG_COLOR[key]}">{len(items)}</b></h4><ul>{lis}</ul></div>''')
    electrified = [c for c in CARS if c["meta"][1] != "بنزين"]
    chips = "".join(
        f'<div><span class="en">{esc(c["name_en"])}</span>'
        f'<span class="f">{esc(c["meta"][1])}</span><b>{c["page"]}</b></div>' for c in electrified)
    return page("toc", f'''
    {runhead("المحتويات — الملفات")}
    <div class="toc">
      <h1 style="font-size:26pt">ثمانٍ وأربعون ملفاً</h1>
      <div class="sub">مرتبة بحسب الشريحة، ورقم الصفحة إلى جانب كل اسم.</div>
      <div class="segcols">{"".join(cols)}</div>
      <div class="toc-sec">ما لا يعمل بالبنزين وحده
        <em>سبع من 48: أربع هجينة قابلة للشحن، اثنتان هجينة، وواحدة كهربائية</em></div>
      <div class="chips">{chips}</div>
    </div>''', "المحتويات")


# ------------------------------------------------------------- 6-7 market data
def counts(idx):
    out = {}
    for c in CARS:
        out[c["meta"][idx]] = out.get(c["meta"][idx], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def bars(data, classes):
    mx = max(data.values())
    rows = ""
    for i, (k, v) in enumerate(data.items()):
        rows += (f'<div class="bar {classes[i % len(classes)]}"><span>{esc(k)}</span>'
                 f'<div class="track"><div class="fill" style="width:{v / mx * 100:.1f}%"></div></div>'
                 f'<span class="v">{v}</span></div>')
    return rows


def market_1():
    o, f = counts(0), counts(1)
    bins = [(30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    hist = [sum(1 for c in CARS if b * 1000 <= c["low"] < e * 1000) for b, e in bins]
    mx = max(hist)
    cols = ""
    for (b, e), v in zip(bins, hist):
        h = 8 + (v / mx) * 86
        cols += (f'<div class="col"><div class="n">{v}</div>'
                 f'<div class="b{" hot" if v == mx else ""}" style="height:{h:.0f}%"></div>'
                 f'<div class="x"><bdi dir="ltr">{b}–{e}</bdi></div></div>')
    return page("data", f'''
    {runhead(MARKET["kicker"])}
    <div class="data">
      <h1>{esc(MARKET["title"])}</h1>
      <p class="lede" style="max-width:140mm">{esc(MARKET["lede"])}</p>
      <div class="chart"><h3>{esc(MARKET["q1"])}</h3>{bars(o, ["a1", "a3", "a2", "a4"])}
        <div class="cap"><b>الشكل 1</b> — {esc(MARKET["c1"])}</div></div>
      <div class="chart"><h3>{esc(MARKET["q2"])}</h3>{bars(f, ["", "a1", "a2", "a3"])}
        <div class="cap"><b>الشكل 2</b> — {esc(MARKET["c2"])}</div></div>
      <div class="chart"><h3>{esc(MARKET["q3"])}</h3>
        <div class="hist">{cols}</div>
        <div class="cap"><b>الشكل 3</b> — {esc(MARKET["c3"])}</div></div>
    </div>''', "لمحة على السوق")


def market_2():
    rated = [c for c in CARS if c["rating"]]
    pts = ""
    for c in rated:
        x = (c["low"] - 30000) / 70000 * 100
        y = (float(c["rating"]) - 7.4) / 2.2 * 100
        pts += f'<div class="pt" style="right:{x:.1f}%;bottom:{y:.1f}%;background:{SEG_COLOR[c["seg"]]}"></div>'
    for en, anchor in (("Toyota Corolla", ""), ("BYD Qin Plus DM-i", ""), ("Nissan Sunny", ""),
                       ("Chery Arrizo 5", " edge-r"), ("Honda Civic", " edge-l")):
        c = find(en)
        x = (c["low"] - 30000) / 70000 * 100
        y = (float(c["rating"]) - 7.4) / 2.2 * 100
        pts += (f'<div class="lbl{anchor}" style="right:{x:.1f}%;bottom:calc({y:.1f}% + 2.6mm)">'
                f'{esc(c["name_en"])}</div>')
    grid = "".join(f'<div class="gl" style="bottom:{p}%"></div>' for p in (25, 50, 75))
    cheap = sorted(CARS, key=lambda c: c["low"])[:5]
    dear = sorted(CARS, key=lambda c: -c["low"])[:5]
    segrows = ""
    for label, key in [("الدخول", "entry"), ("الاستخدام اليومي", "daily"),
                       ("العائلية", "family"), ("قرب السقف", "cap")]:
        items = [c for c in CARS if c["seg"] == key]
        rs = [float(c["rating"]) for c in items if c["rating"]]
        segrows += (f'<div class="row"><span><i style="background:{SEG_COLOR[key]}"></i>{esc(label)}</span>'
                    f'<span class="num">{len(items)}</span>'
                    f'<span class="num">{min(c["low"] for c in items):,}</span>'
                    f'<span class="num">{max(c["high"] for c in items):,}</span>'
                    f'<span class="num">{sum(rs)/len(rs):.1f}</span></div>')

    def side(title, items, note):
        rows = "".join(
            f'<li><span class="en">{esc(c["name_en"])}</span>'
            f'<span class="pz"><bdi dir="ltr">{c["low"]:,}</bdi></span>'
            f'<b>{c["page"]}</b></li>' for c in items)
        return (f'<div class="extreme"><h4>{esc(title)}</h4><ol>{rows}</ol>'
                f'<p>{esc(note)}</p></div>')

    return page("data", f'''
    {runhead("لمحة على السوق")}
    <div class="data">
      <div class="chart" style="margin-top:3mm"><h3>{esc(MARKET["q4"])}</h3>
        <div class="scatter">{grid}{pts}
          <div class="ax" style="bottom:-5.4mm;right:0">30 ألفاً</div>
          <div class="ax" style="bottom:-5.4mm;left:0">100 ألف</div>
          <div class="ax" style="top:-1mm;left:-9mm">9.5</div>
          <div class="ax" style="bottom:-1.4mm;left:-9mm">7.5</div>
          <div class="ax" style="bottom:49%;left:-9mm">8.5</div>
        </div>
        <div class="cap" style="margin-top:7mm"><b>الشكل 4</b> — {esc(MARKET["c4"])}</div></div>
      <div class="extremes">
        {side("الأرخص خمساً", cheap, "خمس سيارات تفتح باب السوق الجديد بأقل مبلغ ممكن.")}
        {side("الأعلى خمساً", dear, "خمس سيارات تقف عند الحافة العليا للسقف، بلا هامش تقريباً.")}
      </div>
      <div class="segtable">
        <div class="hdr"><span>الشريحة</span><span>عدد</span><span>من</span><span>إلى</span>
          <span>متوسط التقييم</span></div>
        {segrows}
      </div>
      <div class="keyfacts">
        <div><b>68,000</b><span>وسيط أسعار الدخول داخل العدد · درهم</span></div>
        <div><b>8.5</b><span>متوسط تقييم أنوكار للسيارات المُقيَّمة</span></div>
        <div><b>9.4</b><span>أعلى تقييم في العدد — تويوتا كورولا</span></div>
      </div>
    </div>''', "لمحة على السوق")


# --------------------------------------------------------------- car profiles
def spec_grid(car):
    cells = ""
    for s in car["specs"]:
        val, unit = s["value"], s["unit"]
        ar = re.search(r"[؀-ۿ]", val)
        u = f'<u>{esc(unit)}</u>' if unit and not ar and val != "—" else ""
        # a Latin-only value is one LTR object; a mixed one keeps its Arabic flow
        shown = esc(val) if ar else f'<bdi dir="ltr">{esc(val, isolate=False)}</bdi>'
        cells += (f'<div class="s"><dt>{esc(s["label"])}</dt>'
                  f'<dd class="{"ar" if ar else ""}">{shown}{u}</dd></div>')
    return f'<div class="specs">{cells}</div>'


def price_bar(car):
    upd = car.get("price_updated")
    third = (f'<div class="alt"><dt>السعر المحدَّث</dt><dd>{esc(upd)}</dd></div>' if upd else
             f'<div class="alt"><dt>الشريحة</dt><dd class="arabic">'
             f'{esc(car["meta"][2].replace("شريحة ", ""))}</dd></div>')
    return f'''<dl class="pricebar">
      <div><dt>سعر العدد · درهم</dt><dd>{esc(money(car["price"]))}</dd></div>
      <div><dt>المنظومة</dt><dd style="font-family:'Plex AR';font-size:10.5pt;font-weight:500">
        {esc(car["meta"][1])}</dd></div>
      {third}</dl>'''


def meter(car):
    lo = max(0, (car["low"] - 30000) / 70000 * 100)
    hi = min(100, (car["high"] - 30000) / 70000 * 100)
    width = max(hi - lo, 1.5)
    return f'''<div class="meter">
      <div class="lbl"><span>موقع السعر داخل السقف</span><span>30 – 100 ألف درهم</span></div>
      <div class="track"><div class="span" style="right:{lo:.1f}%;width:{width:.1f}%"></div></div>
      <div class="ticks"><span>30k</span><span>50k</span><span>70k</span><span>100k</span></div>
    </div>'''


def nextup(car):
    cells = ""
    for a in car["alternatives"][:3]:
        c = find(a["name"].strip())
        pg = f'صفحة {c["page"]}' if c else ""
        cells += (f'<div><div class="n en">{esc(a["name"].strip())}</div>'
                  f'<div class="pz">{esc(a["price"])}</div>'
                  f'<div style="font-size:6.6pt;color:var(--muted);margin-top:.8mm">{esc(pg)}</div></div>')
    return (f'<div class="nextup"><h4>اجلس في هذه بعدها</h4>'
            f'<div class="row">{cells}</div></div>')


def plists(car):
    s = "".join(f"<li>{esc(x)}</li>" for x in car["strengths"])
    w = "".join(f"<li>{esc(x)}</li>" for x in car["caveats"])
    return f'''<div class="twocol">
      <div class="plist"><h4><i>+</i>نقاط القوة</h4><ul>{s}</ul></div>
      <div class="plist warn"><h4><i>!</i>قبل أن تشتري</h4><ul>{w}</ul></div>
    </div>'''


def verdict(car, dark=False):
    return f'''<div class="verdict{' dark' if dark else ''}">
      <h4>رأي المحرر</h4><p>{esc(car["verdict"])}</p>
      <div class="fit"><b>مناسبة لـ</b> {esc(car["fit"])}</div></div>'''


def photo(car, cls="bleed"):
    tag = "إضافة محدَّثة" if not car["rating"] else car["meta"][0]
    return f'''<figure class="photo {cls}"><img src="../assets/img/{car["image"]}">
      <figcaption class="credit">{esc(car["credit"])}</figcaption>
      <div class="tag">{esc(tag)}</div></figure>'''


def head_line(car):
    return (f'<div class="head"><span class="seg">{esc(car["meta"][2])}</span>'
            f'<span class="rk"><bdi dir="ltr">{car["rank"]:02d} / 48</bdi></span>'
            f'<span>{esc(car["meta"][0])} · {esc(car["meta"][1])}</span></div>')


def title_block(car):
    if car["rating"]:
        score = f'<div class="score"><b>{car["rating"]}</b><span>تقييم أنوكار</span></div>'
    else:
        score = '<div class="score unrated"><b>—</b><span>إضافة محدَّثة</span></div>'
    return f'''<div class="title">
      <div><h1>{esc(car["name_ar"])}</h1><div class="en">{esc(car["name_en"])}</div></div>
      {score}</div>'''


def car_page(car, layout):
    if layout == "hero":
        inner = f'''
        <div class="masthead">
          {photo(car, "")}
          <div class="ribbon">اختيار المحرر</div>
          <div class="htitle">
            <div>
              {head_line(car)}
              <h1>{esc(car["name_ar"])}</h1><div class="en">{esc(car["name_en"])}</div>
            </div>
            <div class="score"><b>{car["rating"]}</b><span>تقييم أنوكار</span></div>
          </div>
        </div>
        <div class="lower">
          {price_bar(car)}{spec_grid(car)}{plists(car)}{verdict(car, dark=True)}{meter(car)}{nextup(car)}
        </div>'''
        cls = f'car hero {car["seg"]}'
    elif layout == "b":
        inner = (head_line(car) + title_block(car) + photo(car) + price_bar(car) +
                 spec_grid(car) + plists(car) + verdict(car) + meter(car) + nextup(car))
        cls = f'car b {car["seg"]}'
    else:
        inner = (head_line(car) + title_block(car) + price_bar(car) + spec_grid(car) +
                 photo(car) + plists(car) + verdict(car, dark=True) + meter(car) + nextup(car))
        cls = f'car c {car["seg"]}'
    return page(cls, inner, car["meta"][2], car["page"])


# ------------------------------------------------------------- 8 anatomy page
def anatomy():
    """A real profile page, shrunk and annotated — the guide to reading the guide."""
    demo = find("Chery Arrizo 5")
    mini_inner = (head_line(demo) + title_block(demo) + photo(demo, "") + price_bar(demo) +
                  spec_grid(demo) + plists(demo) + verdict(demo) + meter(demo) + nextup(demo))
    # positions measured off a rendered profile page so each dot lands on its part
    markers = [("01", 6.0), ("02", 11.6), ("03", 39.9), ("04", 48.5),
               ("05", 59.5), ("06", 82.3), ("07", 90.7)]
    dots = "".join(f'<span class="mk" style="top:{t}%">{n}</span>' for n, t in markers)
    calls = "".join(
        f'<div class="call"><span class="n">{esc(n)}</span>'
        f'<div><b>{esc(t)}</b>{esc(b)}</div></div>'
        for n, t, b in ANATOMY["calls"])
    legend = "".join(
        f'<div style="border-color:{SEG_COLOR[k]}"><b>{esc(t)}</b>{esc(d)}</div>'
        for t, d, k in ANATOMY["segments"])
    return page("anatomy", f'''
    {runhead(ANATOMY["kicker"])}
    <div class="anatomy">
      <h1 style="font-size:25pt;margin:4mm 0 2.5mm">{esc(ANATOMY["title"])}</h1>
      <p class="lede" style="max-width:150mm;font-size:10pt">{esc(ANATOMY["lede"])}</p>
      <div class="split">
        <div class="mini-wrap">
          <div class="mini"><div class="page recto car b entry mini-page">{mini_inner}</div></div>
          {dots}
          <div class="mini-cap">نموذج: صفحة <bdi dir="ltr">{demo["page"]}</bdi> — {esc(demo["name_ar"])}</div>
        </div>
        <div class="calls">{calls}</div>
      </div>
      <div class="legend">{legend}</div>
    </div>''', "كيف تقرأ الدليل")


# ---------------------------------------------------------- 9 section opener
def opener():
    segs = ""
    for label, key in [("الدخول", "entry"), ("الاستخدام اليومي", "daily"),
                       ("العائلية", "family"), ("قرب السقف", "cap")]:
        items = [c for c in CARS if c["seg"] == key]
        lo = min(c["low"] for c in items)
        segs += (f'<div><b>{len(items)}</b><span>{esc(label)}</span>'
                 f'<u>من <bdi dir="ltr">{lo:,}</bdi> درهم</u></div>')
    hero = find("Mazda 3 Sedan")
    return page("dark opener", f'''
    <div class="opener" style="height:100%">
      <div>
        <div class="kicker" style="color:#e0725f">القسم الأول</div>
        <div class="bignum">48</div>
        <h1 class="big" style="color:var(--paper);margin-top:3mm">ثمانٍ وأربعون<br>سيدان</h1>
        <p class="lede" style="color:#b6afa2;max-width:118mm;margin-top:5mm">
          صفحة لكل سيارة: الأرقام، ما تجيده، ما يجب أن تعرفه قبل التوقيع، ورأي المحرر في سطرين.
          الترتيب من أرخص سعر دخول إلى أعلاه.</p>
      </div>
      <div><div class="band bleed"><img src="../assets/img/{hero["image"]}"></div>
        <div class="segstrip">{segs}</div></div>
      <div style="display:flex;justify-content:space-between;color:#8d8579;font-family:'Plex Mono','Plex AR';
                  font-size:7pt;border-top:.4pt solid #3a3f47;padding-top:3mm">
        <span>الصفحات <bdi dir="ltr">{FIRST_CAR_PAGE} — {FIRST_CAR_PAGE + 47}</bdi></span>
        <span>{ISSUE["site"]}</span></div>
    </div>''', "ثمانٍ وأربعون سيدان")


# ------------------------------------------------------------- 58 editor picks
def picks_page():
    rows = ""
    for i, (en, why) in enumerate(PICKS["items"], 1):
        c = find(en)
        rows += f'''<div class="pick">
          <div class="ph"><img src="../assets/img/{c["image"]}"></div>
          <div><div class="no">{i:02d} · صفحة {c["page"]}</div><h3>{esc(c["name_ar"])}</h3>
            <div class="en">{esc(c["name_en"])} · <span class="num">{esc(c["price"])}</span> درهم</div>
            <div class="why">{esc(why)}</div></div>
          <div class="sc"><b>{c["rating"]}</b><span><bdi dir="ltr">/ 10</bdi></span></div></div>'''
    return page("picks", f'''
    {runhead(PICKS["kicker"])}
    <div class="picks"><h1>{esc(PICKS["title"])}</h1>
      <p class="lede" style="max-width:140mm;margin-bottom:5mm">{esc(PICKS["lede"])}</p>
      {rows}</div>''', "اختيارات المحرر", PAGE_PICKS)


# --------------------------------------------------------- 59 best per segment
def best_page():
    blocks = ""
    for label, key in [("شريحة الدخول", "entry"), ("شريحة الاستخدام اليومي", "daily"),
                       ("شريحة العائلية", "family"), ("شريحة قرب السقف", "cap")]:
        pool = [c for c in CARS if c["seg"] == key and c["rating"]]
        win = max(pool, key=lambda c: float(c["rating"]))
        cheap = min([c for c in CARS if c["seg"] == key], key=lambda c: c["low"])
        blocks += f'''<div class="pick" style="border-top-color:{SEG_COLOR[key]};border-top-width:2.4pt">
          <div class="ph"><img src="../assets/img/{win["image"]}"></div>
          <div><div class="no" style="color:{SEG_COLOR[key]}">{esc(label)} · صفحة {win["page"]}</div>
            <h3>{esc(win["name_ar"])}</h3>
            <div class="en">{esc(win["name_en"])} · <span class="num">{esc(win["price"])}</span> درهم</div>
            <div class="why">{esc(win["fit"])} أرخص مدخل داخل الشريحة:
              <span class="en">{esc(cheap["name_en"])}</span> عند
              <span class="num"><bdi dir="ltr">{cheap["low"]:,}</bdi></span> درهم (صفحة {cheap["page"]}).</div></div>
          <div class="sc"><b>{win["rating"]}</b><span><bdi dir="ltr">/ 10</bdi></span></div></div>'''
    return page("picks best", f'''
    {runhead("الأفضل في كل شريحة")}
    <div class="picks"><h1 style="font-size:28pt">أربع شرائح، أربعة قرارات</h1>
      <p class="lede" style="max-width:140mm;margin-bottom:5mm">
        السقف واحد، لكن الاحتياج ليس واحداً. هذه أعلى سيارة مُقيَّمة داخل كل شريحة، ومعها أرخص
        مدخل إلى الشريحة نفسها إذا كانت الميزانية هي الحكم.</p>
      {blocks}
      <p class="closing">القاعدة نفسها في الشرائح الأربع: الفارق بين أعلى تقييم وأرخص مدخل هو ما
        تدفعه مقابل الاعتمادية وشبكة الخدمة وقيمة إعادة البيع، لا مقابل الشكل. إذا كان الفارق أقل من
        عشرة آلاف درهم، فالأعلى تقييماً يستحق التجربة أولاً.</p>
    </div>''', "الأفضل في كل شريحة", PAGE_BEST)


# -------------------------------------------------------------- 60-61 index
def index_page(part, cars):
    rows = ""
    for c in cars:
        dot = ORIGIN_COLOR.get(c["meta"][0], "#999")
        rows += f'''<tr><td class="n">{c["rank"]:02d}</td>
          <td class="car-en">{esc(c["name_en"])}</td>
          <td><span class="dot" style="background:{dot}"></span>{esc(c["meta"][0])}</td>
          <td>{esc(c["meta"][1])}</td>
          <td class="pz">{esc(c["price"])}</td>
          <td class="rt">{c["rating"] or "—"}</td>
          <td class="pg">{c["page"]}</td></tr>'''
    if part == 1:
        title, lede = "الفهرس الكامل", (
            '<p class="lede" style="max-width:145mm;margin-bottom:1mm">كل السيارات التي دخلت المقارنة، '
            'مرتبة بحسب أقل سعر مؤهل داخل سقف الدليل. رقم الصفحة يقود إلى الملف الكامل.</p>')
        foot = ('<div class="legend-row">'
                + "".join(f'<span><i style="background:{v}"></i>{esc(k)}</span>'
                          for k, v in ORIGIN_COLOR.items())
                + '<span class="note-inline">النقطة الملونة تشير إلى منشأ العلامة، لا إلى بلد التجميع.</span></div>')
    else:
        title, lede = "الفهرس الكامل — تتمة", ""
        foot = '''<div class="index-notes">
          <div><b>التقييم</b> من عشرة، ويجمع السعر مقابل التجهيز، والاعتمادية، وشبكة الخدمة،
            وقيمة إعادة البيع المتوقعة داخل الدولة.</div>
          <div><b>الشرطة (—)</b> تعني إضافة محدَّثة دخلت العدد بعد إغلاق التقييم، وتُقرأ كمرجع سعري
            لا كترتيب.</div>
          <div><b>السعر</b> نطاق يبدأ من أقل فئة مؤهلة داخل السقف وينتهي عند أعلى فئة رصدها البحث؛
            العرض النهائي يبقى مسألة تفاوض.</div>
        </div>'''
    return page("index", f'''
    {runhead("الفهرس")}
    <div class="index"><h1>{esc(title)}</h1>{lede}
      <table class="itab"><thead><tr><th>#</th><th>السيارة</th><th>المنشأ</th><th>المنظومة</th>
        <th>السعر (درهم)</th><th>التقييم</th><th>صفحة</th></tr></thead>
        <tbody>{rows}</tbody></table>
      {foot}</div>''', "الفهرس", PAGE_INDEX + part - 1)


# ------------------------------------------------------------- 62 brand guide
def brands_page():
    groups = {}
    for c in CARS:
        brand = "Lynk & Co" if c["name_en"].startswith("Lynk") else c["name_en"].split()[0]
        groups.setdefault(brand, []).append(c)
    html = ""
    for brand in sorted(groups):
        items = sorted(groups[brand], key=lambda c: c["low"])
        lis = "".join(
            f'<li><span class="en">{esc(c["name_en"].replace(brand, "").strip() or brand)}</span>'
            f'<b>{c["page"]}</b></li>' for c in items)
        html += f'<div class="brand"><h4>{esc(brand)}</h4><ul>{lis}</ul></div>'
    o = counts(0)
    foot = "".join(f'<div><b>{v}</b><span>{esc(k)}</span></div>' for k, v in o.items())
    return page("index", f'''
    {runhead("دليل العلامات")}
    <div class="index"><h1>دليل العلامات</h1>
      <p class="lede" style="max-width:145mm">
        {len(groups)} علامة داخل السقف. إذا كنت تعرف الاسم الذي تريده، ابدأ من هنا.</p>
      <div class="brands">{html}</div>
      <div class="keyfacts brandfoot">{foot}</div>
      <p class="body" style="color:var(--muted);margin-top:3mm">
        العلامات الصينية تشغل أكثر من نصف الأسماء داخل هذا السقف، وهي أيضاً الأسرع تغيّراً في
        الأسعار والفئات؛ راجع سنة الصنع والفئة قبل المقارنة.</p>
    </div>''', "دليل العلامات", PAGE_BRANDS)


# ------------------------------------------------------------ 63 buying guide
def guide_page():
    steps = "".join(
        f'<div class="step"><span class="n">{i}</span><div><h3>{esc(t)}</h3><p>{esc(b)}</p></div></div>'
        for i, (t, b) in enumerate(GUIDE["steps"], 1))
    checks = ["سنة الصنع والفئة ورقم الهيكل مطابقة للعرض",
              "الضمان مكتوب: المدة، الكيلومترات، والاستثناءات",
              "تسعيرة تأمين فعلية لهذه الفئة تحديداً",
              "تكلفة أول ثلاث صيانات دورية",
              "توفر قطع الغيار ومدة انتظارها",
              "تجربة قيادة على طريقك اليومي، لا حول المعرض"]
    checklist = "".join(f'<li>{esc(x)}</li>' for x in checks)
    t1, t2 = GUIDE["title"].split("\n")
    return page("guide", f'''
    {runhead(GUIDE["kicker"])}
    <div class="guide"><h1>{esc(t1)}<br>{esc(t2)}</h1>
      <p class="lede" style="max-width:138mm;margin-bottom:6mm">{esc(GUIDE["lede"])}</p>
      {steps}
      <div class="checklist"><h4>قائمة تحقق سريعة قبل التوقيع</h4><ul>{checklist}</ul></div>
      <div class="cta"><div><h3>{esc(GUIDE["cta_title"])}</h3><p>{esc(GUIDE["cta_body"])}</p></div>
        <div class="w"><div class="wordmark">{ISSUE["brand"]}</div><div>{ISSUE["brand_sub"]}</div></div>
      </div></div>''', "قبل أن تشتري", PAGE_GUIDE)


# ---------------------------------------------------------------- 64 back cover
def back_cover():
    hero = find("Geely Preface")
    return page("back", f'''
    <div><div class="wordmark">{ISSUE["brand"]}</div>
      <div class="wm-sub">{ISSUE["brand_sub"]}</div>
      <h2>{esc(BACK["title"])}</h2></div>
    <div class="band"><img src="../assets/img/{hero["image"]}"></div>
    <div>
      <div class="facts">
        <div><dt>عدد السيارات</dt><dd>48</dd></div>
        <div><dt>النطاق السعري</dt><dd>31,500 – 99,900</dd></div>
        <div><dt>قطع البحث</dt><dd>25.08.2026</dd></div>
        <div><dt>الإصدار</dt><dd>1.0</dd></div>
      </div>
      <p class="fine" style="margin-top:8mm">{esc(BACK["fine"])}</p>
      <div class="site">{ISSUE["site"]}</div>
    </div>''')


# --------------------------------------------------------------------- assemble
def main():
    add(cover()); add(imprint()); add(letter()); add(contents_1()); add(contents_2())
    add(market_1()); add(market_2()); add(anatomy()); add(opener())
    alt = 0
    for c in CARS:
        if c["rating"] and float(c["rating"]) >= 9.0:
            layout = "hero"
        else:
            layout = "b" if alt % 2 == 0 else "c"
            alt += 1
        add(car_page(c, layout))
    add(picks_page()); add(best_page())
    add(index_page(1, CARS[:24])); add(index_page(2, CARS[24:]))
    add(brands_page()); add(guide_page()); add(back_cover())

    html = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<title>{ISSUE["brand"]} — {ISSUE["title"]}</title>
<link rel="stylesheet" href="../assets/magazine.css"></head><body>
{"".join(PAGES)}
</body></html>'''
    OUT.write_text(html, encoding="utf-8")
    print(f"pages={len(PAGES)}  ->  {OUT}")


if __name__ == "__main__":
    main()
