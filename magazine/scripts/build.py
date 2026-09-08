#!/usr/bin/env python3
"""Compose the AnoKar issue: front of book, feature well, buyer's guide."""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from copy_ar import (ISSUE, COVER, LETTER, METHOD, RADAR, FEATURE, DATA, GROUP,
                     H2H, CHINA, SEGMENTS, BOB, CLOSE, BACK)

ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = json.loads((ROOT / "build" / "content.json").read_text(encoding="utf-8"))
CARS = DATA_JSON["cars"]
OUT = ROOT / "build" / "magazine.html"

SEG_KEY = {"شريحة الدخول": "entry", "شريحة الاستخدام اليومي": "daily",
           "شريحة العائلية": "family", "شريحة قرب السقف": "cap"}
SEG_NAME = {"entry": "شريحة الدخول", "daily": "شريحة الاستخدام اليومي",
            "family": "شريحة العائلية", "cap": "شريحة قرب السقف"}
SEG_COLOR = {"entry": "#B8462B", "daily": "#2B6B52", "family": "#21456B", "cap": "#7C5A2C"}
ORIGIN_COLOR = {"الصين": "#D5301F", "اليابان": "#21456B", "كوريا": "#2B6B52", "أوروبا": "#7C5A2C"}

RANGE = re.compile(r"\d[\d.,]*[A-Za-z]*(?:\s*[–—/-]\s*\d[\d.,]*[A-Za-z]*)+")


def esc(t, isolate=True):
    t = (t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if isolate:                       # keep bidi from re-ordering "31,500 – 43,500"
        t = RANGE.sub(lambda m: f'<bdi dir="ltr">{m.group(0)}</bdi>', t)
    return t


def num(v):
    return f'<bdi dir="ltr">{v}</bdi>'


def low(p):
    m = re.search(r"([\d,]+)", p or "")
    return int(m.group(1).replace(",", "")) if m else 0


def high(p):
    n = re.findall(r"([\d,]+)", p or "")
    return int(n[-1].replace(",", "")) if n else 0


for c in CARS:
    c["seg"] = SEG_KEY.get(c["meta"][2], "daily")
    c["low"], c["high"] = low(c["price"]), high(c["price"])
    c["score"] = float(c["rating"]) if c["rating"] else None
    c["img"] = f'../assets/img/{c["image"]}'


def by_en(name):
    for c in CARS:
        if c["name_en"] == name:
            return c
    for c in CARS:
        if c["name_en"].startswith(name[:14]):
            return c
    return None


def spec(car, label):
    for s in car["specs"]:
        if s["label"] == label:
            return s
    return {"label": label, "value": "—", "unit": ""}


FINALISTS = [c for c in sorted(CARS, key=lambda c: (-(c["score"] or 0), c["low"])) if c["score"] and c["score"] >= 9.0]
RUNNERS = [c for c in sorted(CARS, key=lambda c: (-(c["score"] or 0), c["low"])) if c["score"] and 8.5 < c["score"] < 9.0]

# ------------------------------------------------------------------ pagination
PAGES = []
PLAN = {}          # symbolic name -> page number, filled while assembling


def page(cls, inner, section=None, folio=True):
    n = len(PAGES) + 1
    par = "odd" if n % 2 else "even"
    f = ""
    if folio:
        f = (f'<div class="folio"><span>{ISSUE["brand"]} · {esc(ISSUE["issue_line"])}</span>'
             f'<span>{esc(section or "")}</span><b>{n}</b></div>')
    PAGES.append(f'<section class="page {par} {cls}" data-pg="{n}">{inner}{f}</section>')
    return n


def sec(label, extra=""):
    lat = f'<i>{extra}</i>' if extra else ""
    return f'<div class="sec">{esc(label)}{lat}</div>'


# ---------------------------------------------------------------------- cover
def cover(refs):
    hero = by_en("Toyota Corolla")
    lines = "".join(
        f'<li><div><b>{esc(t)}</b><em>{esc(s)}</em></div>'
        f'<span class="pg">صفحة {refs[k]}</span></li>' for t, s, k in COVER["lines"])
    h1 = COVER["head"].replace("\n", "<br>")
    return page("cover flush", f'''
      <div class="bgshot"><img src="{hero["img"]}"></div>
      <div class="strip"><img src="{hero["img"]}"></div>
      <div class="scrim"></div>
      <div class="mast">
        <div class="name">{ISSUE["brand"]}</div>
        <div class="sub"><span>{esc(ISSUE["issue_line"])}</span>
          <span class="lat">ISSUE 01 — UAE</span></div>
      </div>
      <div class="flash"><b>{COVER["flash_num"]}</b><span>{esc(COVER["flash_txt"])}</span></div>
      <div class="head"><div class="kick">{esc(COVER["kicker"])}</div>
        <h1>{h1}</h1><p>{esc(COVER["stand"])}</p></div>
      <ul class="lines">{lines}</ul>
      <div class="foot"><span>{ISSUE["site"]}</span>
        <span>قطع البحث {ISSUE["cutoff"]}</span></div>''', folio=False)


# -------------------------------------------------------------------- contents
def contents(toc_rows):
    feats = ""
    for en, cap, pg in toc_rows["features"]:
        c = by_en(en)
        feats += (f'<figure><img src="{c["img"]}">'
                  f'<figcaption><div class="t">{esc(cap)}</div>'
                  f'<div class="p">صفحة {pg}</div></figcaption></figure>')
    blocks = ""
    for title, rows in toc_rows["blocks"]:
        r = "".join(f'<div class="toc-row"><span class="n">{p}</span>'
                    f'<span class="t">{esc(t)}</span><span class="d">{esc(d)}</span></div>'
                    for p, t, d in rows)
        blocks += f'<div class="toc-block"><h4>{esc(title)}</h4>{r}</div>'
    return page("toc", f'''
      {sec("المحتويات", "CONTENTS")}
      <h1 style="margin:4mm 0 1mm">{esc(ISSUE["title"])}</h1>
      <p class="cap" style="font-size:8.4pt">{esc(ISSUE["issue_line"])}</p>
      <div class="big">{feats}</div>
      {blocks}''', "المحتويات")


# ------------------------------------------------------------- editor's letter
def letter():
    ps = "".join(f"<p>{esc(p)}</p>" for p in LETTER["paras"])
    t = LETTER["title"].replace("\n", "<br>")
    return page("letter", f'''
      {sec(LETTER["kick"], "EDITOR'S LETTER")}
      <h1>{t}</h1>
      <p class="open">{esc(LETTER["open"])}</p>
      <div class="cols">{ps}</div>
      <div class="sign"><b>{esc(LETTER["sign"])}</b><span>{ISSUE["site"]}</span></div>''',
                LETTER["kick"])


def methodology():
    rules = "".join(
        f'<div class="item"><b>{n}</b><div><h5>{esc(t)}</h5><p>{esc(b)}</p></div></div>'
        for n, t, b in METHOD["rules"])
    return page("letter", f'''
      {sec(METHOD["kick"], "METHOD")}
      <h1 style="font-size:28pt;margin:4mm 0 3mm">{esc(METHOD["title"])}</h1>
      <p class="stand" style="max-width:140mm">{esc(METHOD["stand"])}</p>
      <div class="rulebox">{rules}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8mm;margin-top:7mm">
        <div><h4 style="font-family:'Display','AR';font-weight:800;font-size:11pt;margin-bottom:2.4mm">
          {esc(METHOD["score_title"])}</h4>
          <p class="copy">{esc(METHOD["score_body"])}</p></div>
        <div><h4 style="font-family:'Display','AR';font-weight:800;font-size:11pt;margin-bottom:2.4mm">
          {esc(METHOD["limits_title"])}</h4>
          <p class="copy">{esc(METHOD["limits_body"])}</p></div>
      </div>
      <div class="scale">
        <div class="lab"><span>ما يعنيه الرقم</span><span>تقييم أنوكار من عشرة</span></div>
        <div class="bandrow">
          <div style="flex:2"><b>7.5 – 7.9</b><span>تشتريها للسعر، وتتعايش مع الباقي</span></div>
          <div style="flex:3"><b>8.0 – 8.4</b><span>صفقة منطقية داخل شريحتها</span></div>
          <div style="flex:3"><b>8.5 – 8.9</b><span>قوية في أكثر من بند، لا في بند واحد</span></div>
          <div style="flex:2;background:var(--red);color:#fff"><b>9.0 +</b>
            <span>تخسر أقل عدد من البنود بعد سنة</span></div>
        </div>
      </div>
      <div class="sidebar" style="margin-top:6mm"><h4>ما لا يقيسه الرقم</h4>
        <p>المتعة خلف المقود، وذوقك في الشكل، وعرض التمويل الذي ستحصل عليه في المعرض.
           هذه ثلاثة بنود لا يستطيع أي جدول أن يقررها بدلاً عنك.</p></div>''', METHOD["kick"])


# ---------------------------------------------------------------------- radar
def radar_items():
    cheap = min(CARS, key=lambda c: c["low"])
    dear = max(CARS, key=lambda c: c["low"])
    ev = [c for c in CARS if c["meta"][1] == "كهربائية"][0]
    phev = [c for c in CARS if c["meta"][1] == "هجينة قابلة للشحن"]
    unrated = [c for c in CARS if not c["score"]]
    spread = max(CARS, key=lambda c: c["high"] - c["low"])
    top = max([c for c in CARS if c["score"]], key=lambda c: c["score"])
    return cheap, dear, ev, phev, unrated, spread, top


def radar_a():
    cheap, dear, ev, phev, unrated, spread, top = radar_items()
    china = sum(1 for c in CARS if c["meta"][0] == "الصين")
    return page("radar", f'''
      {sec(RADAR["kick"], "RADAR")}
      <h1>{esc(RADAR["title"])}</h1>
      <p class="stand" style="margin-top:3mm;max-width:130mm">{esc(RADAR["stand"])}</p>
      <div class="grid">
        <div class="item wide dark" style="display:grid;grid-template-columns:34mm 1fr;gap:6mm;
             align-items:center">
          <div><span class="num">{china}</span><div class="lab">من أصل 48</div></div>
          <div><h3>الصين تكتب قائمة السيدان الاقتصادية</h3>
            <p>تسع وعشرون سيارة صينية داخل السقف، مقابل إحدى عشرة يابانية وستّ كورية
               واثنتين أوروبيتين. الشريحة لم تعد تُكتب في طوكيو.</p></div>
        </div>
        <div class="item"><figure><img src="{cheap["img"]}"></figure>
          <div class="lab">أرخص مدخل</div><span class="num">{cheap["low"]:,}</span>
          <h3>{esc(cheap["name_ar"])}</h3>
          <p>أقل سعر دخول في العدد. سيارة جديدة بضمان بدل مستعملة مجهولة التاريخ —
             صفحة {cheap["page"] if "page" in cheap else ""}.</p></div>
        <div class="item"><figure><img src="{dear["img"]}"></figure>
          <div class="lab">أعلى سعر ابتدائي</div><span class="num">{dear["low"]:,}</span>
          <h3>{esc(dear["name_ar"])}</h3>
          <p>تلامس السقف من دون أن تكسره، وتترك هامشاً يكاد لا يُذكر للتأمين والتسجيل.</p></div>
        <div class="item"><div class="lab">الكهرباء الكاملة</div><span class="num">1</span>
          <h3>سيارة كهربائية واحدة فقط</h3>
          <p>{esc(ev["name_ar"])} هي الخيار الوحيد بلا محرك بنزين تحت مئة ألف درهم، عند
             {num(f'{ev["low"]:,}')} درهم.</p></div>
        <div class="item"><div class="lab">الهجين القابل للشحن</div>
          <span class="num">{len(phev)}</span>
          <h3>الوافد الجديد على الشريحة</h3>
          <p>أربع سيارات تجمع محركاً وبطارية قابلة للشحن. الشرط الوحيد لجدواها: مقبس
             ثابت في المنزل أو العمل.</p></div>
      </div>''', RADAR["kick"])


def radar_b():
    cheap, dear, ev, phev, unrated, spread, top = radar_items()
    bins = [(70, 80)]
    crowd = sum(1 for c in CARS if 70000 <= c["low"] < 80000)
    med = sorted(c["low"] for c in CARS)[len(CARS) // 2]
    imports = [c for c in CARS if "Import" in c["name_en"]]
    return page("radar", f'''
      {sec(RADAR["kick"], "RADAR")}
      <div class="grid" style="margin-top:2mm">
        <div class="item wide" style="border-top:1.6pt solid var(--ink);padding-top:4mm">
          <div style="display:grid;grid-template-columns:34mm 1fr;gap:6mm;align-items:center">
            <div><span class="num">{crowd}</span><div class="lab">سيارات</div></div>
            <div><h3>الازدحام كله بين سبعين وثمانين ألفاً</h3>
              <p>ثلاث عشرة سيارة تتنافس داخل شريحة عرضها عشرة آلاف درهم فقط. هنا يصبح فرق
                 الخمسة آلاف فئة أعلى، لا سيارة أخرى — وهنا يجب أن تصرف أطول وقت في المقارنة.</p></div>
          </div></div>
        <div class="item"><div class="lab">وسيط السوق</div>
          <span class="num">{med:,}</span><h3>نصف القائمة تحت هذا الرقم</h3>
          <p>وسيط أسعار الدخول داخل العدد. إذا كانت ميزانيتك عند هذا الحد، فأمامك نصف
             القائمة فعلياً.</p></div>
        <div class="item"><div class="lab">أعلى تقييم</div>
          <span class="num">{top["rating"]}</span><h3>{esc(top["name_ar"])}</h3>
          <p>أعلى رقم في العدد. لا تفوز في بند واحد، بل تخسر أقل عدد من البنود بعد سنة
             من الملكية.</p></div>
        <div class="item"><div class="lab">أوسع فارق داخل الطراز</div>
          <span class="num">{spread["high"] - spread["low"]:,}</span>
          <h3>{esc(spread["name_ar"])}</h3>
          <p>الفرق بين أرخص فئة وأعلاها داخل الاسم نفسه. اسم السيارة لا يحدد سعرها؛
             الفئة تفعل.</p></div>
        <div class="item dark"><div class="lab">تحذير</div>
          <span class="num">{len(imports)}</span>
          <h3>سيارات تصل عبر الاستيراد</h3>
          <p>السعر أقل، لكن الضمان والبرمجيات وقطع الغيار تحتاج إجابة مكتوبة من بائع مرخص
             داخل الدولة قبل التوقيع.</p></div>
        <div class="item"><div class="lab">بلا تقييم</div>
          <span class="num">{len(unrated)}</span><h3>إضافات محدَّثة دخلت متأخرة</h3>
          <p>سبع سيارات دخلت العدد بعد إغلاق التقييم. تركناها بلا رقم عمداً: وجودها في
             السوق شيء، وإعطاؤها درجة قبل التحقق شيء آخر.</p></div>
      </div>''', RADAR["kick"])


# ------------------------------------------------------------- feature opener
def feature_open():
    hero = by_en("Geely Preface")
    h = FEATURE["title"].replace("\n", "<br>")
    return page("opener flush", f'''
      <div class="bgshot"><img src="{hero["img"]}"></div>
      <div class="strip"><img src="{hero["img"]}"></div>
      <div class="scrim"></div>
      <div class="toplab">{esc(FEATURE["kick"])} · {ISSUE["brand"]} 01</div>
      <div class="txt"><div class="kick">{esc(FEATURE["kick"])}</div>
        <h1>{h}</h1><p>{esc(FEATURE["stand"])}</p>
        <div class="teaser"><p>{esc(FEATURE["paras"][0])}</p><p>{esc(FEATURE["paras"][1])}</p></div>
        <div class="inthis">
          <div><span>الصفحة 09</span><b>السوق بالأرقام</b></div>
          <div><span>الصفحة 11</span><b>الخمسة النهائيون</b></div>
          <div><span>الصفحة 25</span><b>كيف غيّرت الصين القواعد</b></div>
        </div></div>
      <div class="credit">{esc(hero["credit"])}</div>''', folio=False)


def feature_text():
    ps = FEATURE["paras"][2:]          # the first two ran on the opener
    col1 = "".join(f"<p>{esc(p)}</p>" for p in ps[:2])
    col2 = "".join(f"<p>{esc(p)}</p>" for p in ps[2:])
    return page("feat", f'''
      {sec(FEATURE["kick"], "THE BIG STORY")}
      <h1>{esc(FEATURE["head2"])}</h1>
      <div class="cols" style="margin-top:5mm">{col1}{col2}</div>
      <div class="pull"><p>{esc(FEATURE["pull"])}</p>
        <span>{esc(FEATURE["pull_by"])}</span></div>
      <div class="sidebar"><h4>{esc(FEATURE["side_title"])}</h4>
        <p>{esc(FEATURE["side_body"])}</p></div>''', FEATURE["kick"])


# ------------------------------------------------------------------ data pages
def counts(idx):
    o = {}
    for c in CARS:
        o[c["meta"][idx]] = o.get(c["meta"][idx], 0) + 1
    return dict(sorted(o.items(), key=lambda kv: -kv[1]))


def bars(data, colors):
    mx = max(data.values())
    out = ""
    for i, (k, v) in enumerate(data.items()):
        out += (f'<div class="bar"><span>{esc(k)}</span><div class="track">'
                f'<div class="fill" style="width:{v / mx * 100:.1f}%;background:{colors[i % len(colors)]}">'
                f'</div></div><span class="v">{v}</span></div>')
    return out


def data_a():
    o, f = counts(0), counts(1)
    return page("feat", f'''
      {sec(DATA["kick"], "BY THE NUMBERS")}
      <h1 style="font-size:28pt;margin:4mm 0 3mm">{esc(DATA["title"])}</h1>
      <p class="stand" style="max-width:135mm">أربع صور تختصر ما تفعله مئة ألف درهم في هذا السوق.</p>
      <div style="margin-top:7mm">
        <h3 style="font-family:'AR';font-size:10pt;font-weight:600;margin-bottom:4mm">{esc(DATA["q1"])}</h3>
        {bars(o, ["#D5301F", "#21456B", "#2B6B52", "#7C5A2C"])}
        <div class="figcap"><b>الشكل 1</b> — {esc(DATA["c1"])}</div>
      </div>
      <div style="margin-top:7mm">
        <h3 style="font-family:'AR';font-size:10pt;font-weight:600;margin-bottom:4mm">{esc(DATA["q2"])}</h3>
        {bars(f, ["#101315", "#D5301F", "#2B6B52", "#21456B"])}
        <div class="figcap"><b>الشكل 2</b> — {esc(DATA["c2"])}</div>
      </div>
      <div class="stats">
        <div><b>{sum(1 for c in CARS if c["meta"][0] == "الصين")}</b>
          <span>سيارة صينية — أكثر من نصف العدد</span></div>
        <div><b>41</b><span>سيارة تعمل بالبنزين وحده</span></div>
        <div><b>1</b><span>سيارة كهربائية بالكامل</span></div>
      </div>''', DATA["kick"])


def data_b():
    bins = [(30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    hist = [sum(1 for c in CARS if b * 1000 <= c["low"] < e * 1000) for b, e in bins]
    mx = max(hist)
    cols = "".join(
        f'<div class="col"><div class="n">{v}</div>'
        f'<div class="b{" hot" if v == mx else ""}" style="height:{8 + v / mx * 86:.0f}%"></div>'
        f'<div class="x">{num(f"{b}–{e}")}</div></div>' for (b, e), v in zip(bins, hist))
    rated = [c for c in CARS if c["score"]]
    pts = "".join(
        f'<div class="pt" style="right:{(c["low"] - 30000) / 70000 * 100:.1f}%;'
        f'bottom:{(c["score"] - 7.4) / 2.2 * 100:.1f}%;background:{SEG_COLOR[c["seg"]]}"></div>'
        for c in rated)
    for en, cls in (("Toyota Corolla", ""), ("BYD Qin Plus DM-i", ""), ("Nissan Sunny", ""),
                    ("Chery Arrizo 5", " edge-r"), ("Honda Civic", " edge-l")):
        c = by_en(en)
        pts += (f'<div class="lbl{cls}" style="right:{(c["low"] - 30000) / 70000 * 100:.1f}%;'
                f'bottom:calc({(c["score"] - 7.4) / 2.2 * 100:.1f}% + 2.6mm)">{esc(c["name_en"])}</div>')
    grid = "".join(f'<div class="gl" style="bottom:{p}%"></div>' for p in (25, 50, 75))
    med = sorted(c["low"] for c in CARS)[len(CARS) // 2]
    avg = sum(c["score"] for c in rated) / len(rated)
    return page("feat", f'''
      {sec(DATA["kick"], "BY THE NUMBERS")}
      <div style="margin-top:5mm">
        <h3 style="font-family:'AR';font-size:10pt;font-weight:600;margin-bottom:4mm">{esc(DATA["q3"])}</h3>
        <div class="hist">{cols}</div>
        <div class="figcap"><b>الشكل 3</b> — {esc(DATA["c3"])}</div>
      </div>
      <div style="margin-top:7mm">
        <h3 style="font-family:'AR';font-size:10pt;font-weight:600;margin-bottom:4mm">{esc(DATA["q4"])}</h3>
        <div class="scatter">{grid}{pts}
          <div class="ax" style="bottom:-5.4mm;right:0">30 ألفاً</div>
          <div class="ax" style="bottom:-5.4mm;left:0">100 ألف</div>
          <div class="ax" style="top:-1mm;left:-9mm">9.5</div>
          <div class="ax" style="bottom:49%;left:-9mm">8.5</div>
          <div class="ax" style="bottom:-1.4mm;left:-9mm">7.5</div></div>
        <div class="figcap" style="margin-top:7mm"><b>الشكل 4</b> — {esc(DATA["c4"])}</div>
      </div>
      <div class="stats">
        <div><b>{med:,}</b><span>وسيط أسعار الدخول · درهم</span></div>
        <div><b>{avg:.1f}</b><span>متوسط تقييم السيارات المُقيَّمة</span></div>
        <div><b>{max(c["high"] for c in CARS) - min(c["low"] for c in CARS):,}</b>
          <span>المدى الكامل من أرخص فئة إلى أعلاها</span></div>
      </div>''', DATA["kick"])


# ------------------------------------------------------------ group test pages
def group_open():
    board = ""
    for i, c in enumerate(FINALISTS, 1):
        board += f'''<div class="fin">
          <figure><img src="{c["img"]}"></figure>
          <div class="rk">{i:02d}</div>
          <div class="nm"><h3>{esc(c["name_ar"])}</h3>
            <div class="en">{esc(c["name_en"])}</div></div>
          <div class="sc"><b>{c["rating"]}</b></div>
          <div class="pz">{esc(c["price"])} درهم</div></div>'''
    return page("feat group", f'''
      {sec(GROUP["kick"], "GROUP TEST")}
      <h1 style="font-size:34pt;margin:4mm 0 3mm">{esc(GROUP["title"])}</h1>
      <p class="stand" style="max-width:138mm">{esc(GROUP["stand"])}</p>
      <div class="board">{board}</div>''', GROUP["kick"])


def group_how():
    rows = "".join(
        f'<tr><td class="k"><span class="en">{esc(c["name_en"])}</span></td>'
        f'<td class="v">{esc(c["price"])}</td>'
        f'<td class="v">{c["rating"]}</td>'
        f'<td class="v">{c["page"]}</td></tr>' for c in RUNNERS)
    return page("feat", f'''
      {sec(GROUP["kick"], "GROUP TEST")}
      <h1 style="font-size:24pt;margin:4mm 0 3mm">{esc(GROUP["how_title"])}</h1>
      <p class="copy" style="max-width:150mm">{esc(GROUP["how_body"])}</p>
      <div class="pull" style="margin-top:6mm"><p>خمس سيارات فقط تجاوزت تسعة من عشرة.
        الفارق بينها وبين الصف التالي أصغر مما يوحي الرقم.</p></div>
      <h2 style="font-family:'Display','AR';font-weight:800;font-size:15pt;margin-top:2mm">
        {esc(GROUP["runners_title"])}</h2>
      <p class="copy" style="margin-top:2mm">{esc(GROUP["runners_body"])}</p>
      <table class="h2h-table"><thead><tr><th>السيارة</th><th>السعر (درهم)</th>
        <th>التقييم</th><th>صفحة</th></tr></thead><tbody>{rows}</tbody></table>''',
                GROUP["kick"])


def road_test_photo(car, rank):
    alts = ""
    for a in car["alternatives"][:3]:
        c = by_en(a["name"].strip())
        if c:
            alts += (f'<figure><img src="{c["img"]}">'
                     f'<figcaption>{esc(c["name_en"])}</figcaption></figure>')
    quote = car["verdict"].split(".")[0].strip() + "."
    cons = next((s["value"] for s in car["specs"]
                 if "الاستهلاك" in s["label"] or "المدى" in s["label"]), "—")
    quick = [("سعر العدد · درهم", car["price"]),
             ("القوة · حصان", spec(car, "القوة")["value"]),
             ("الاستهلاك", cons)]
    qh = "".join(f'<div><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v in quick)
    return page("rt-photo flush", f'''
      <div class="shot"><img src="{car["img"]}"></div>
      <div class="badge">النهائي {rank:02d} / 05</div>
      <div class="score"><b>{car["rating"]}</b><span>تقييم أنوكار</span></div>
      <div class="body">
        <div class="rank">{esc(car["meta"][0])} · {esc(car["meta"][1])} · {esc(SEG_NAME[car["seg"]])}</div>
        <h1>{esc(car["name_ar"])}</h1>
        <div class="en">{esc(car["name_en"])}</div>
        <div class="quote">{esc(quote)}</div>
        <div class="quick">{qh}</div>
        <div class="gallery"><div class="lab">منافسون مباشرون</div>{alts}</div>
      </div>''', folio=False)


def rt_copy(car):
    """Compose the road-test body from the record's own facts."""
    eng = spec(car, "المحرك")["value"]
    pw = spec(car, "القوة")["value"]
    tq = spec(car, "العزم")["value"]
    gb = spec(car, "ناقل الحركة")["value"]
    acc = spec(car, "0–100 كم/س")["value"]
    cons = next((s["value"] for s in car["specs"] if "الاستهلاك" in s["label"] or "المدى" in s["label"]), "—")
    yr = spec(car, "الموديل")["value"]
    ps = []
    bits = [f'المحرك {eng}']
    if pw not in ("—", "غير موحد"):
        bits.append(f'بقوة {pw} حصان')
    if tq not in ("—", "غير موحد"):
        bits.append(f'وعزم {tq} نيوتن·م')
    ps.append(f'موديل {yr}، {"، ".join(bits)}، عبر ناقل {gb}.' +
              (f' التسارع إلى مئة كم/س عند {acc} ثانية.' if acc not in ("—", "حسب النسخة") else "") +
              (f' الاستهلاك المعلن {cons}.' if cons != "—" else ""))
    ps.append("ما يجعلها تصعد إلى القائمة النهائية بند واحد قبل غيره: " +
              car["strengths"][0].rstrip(".") + ". " +
              (car["strengths"][1] if len(car["strengths"]) > 1 else ""))
    ps.append("وما يجب أن تعرفه قبل التوقيع: " + car["caveats"][0].rstrip(".") + "، و" +
              (car["caveats"][1][0].lower() + car["caveats"][1][1:] if len(car["caveats"]) > 1 else ""))
    names = "، ".join(a["name"].strip() for a in car["alternatives"][:3])
    ps.append(f'داخل الميزانية نفسها تقريباً تجد {names}. قارنها بالفئة لا بالاسم، '
              f'واطلب عرضاً مكتوباً لكل واحدة قبل أن تحسم.')
    return ps


def spec_row(s):
    ar = re.search(r"[؀-ۿ]", s["value"])
    val = esc(s["value"]) if ar else num(esc(s["value"], False))
    unit = f'<u>{esc(s["unit"])}</u>' if s["unit"] and not ar and s["value"] != "—" else ""
    return f'<div class="r"><span>{esc(s["label"])}</span><b>{val}{unit}</b></div>'


def road_test_text(car, rank):
    rows = "".join(spec_row(s) for s in car["specs"])
    ps = "".join(f"<p>{esc(p)}</p>" for p in rt_copy(car))
    likes = "".join(f"<li>{esc(x)}</li>" for x in car["strengths"])
    nos = "".join(f"<li>{esc(x)}</li>" for x in car["caveats"])
    upd = (f'<div class="r"><span>السعر المحدَّث</span><b>{esc(car["price_updated"])}</b></div>'
           if car.get("price_updated") else "")
    return page("rt-text", f'''
      {sec(f'النهائي {rank:02d}', "ROAD TEST")}
      <div class="head" style="margin-top:4mm">
        <div><h2>{esc(car["name_ar"])}</h2>
          <div class="en">{esc(car["name_en"])}</div></div>
        <div style="text-align:left"><div class="mono" style="font-size:15pt;font-weight:700">
          {esc(car["price"])}</div>
          <div class="cap">درهم · سعر العدد</div></div>
      </div>
      <div class="cols" style="margin-top:5mm">{ps}</div>
      <div class="verdict-grid">
        <div class="vcol"><h4><i>+</i>ما يعجبنا</h4><ul>{likes}</ul></div>
        <div class="vcol no"><h4><i>!</i>ما يجب التحقق منه</h4><ul>{nos}</ul></div>
      </div>
      <div class="spec-table">{rows}{upd}</div>
      <div class="verdict-box"><h4>الحكم</h4><p>{esc(car["verdict"])}</p>
        <div class="fit"><b>مناسبة لـ</b> {esc(car["fit"])}</div></div>''', "الاختبار الجماعي")


# ------------------------------------------------------------------ head to head
def h2h_page():
    a, b = by_en("Toyota Corolla"), by_en("BYD Qin Plus DM-i")

    def cell(car, key):
        return spec(car, key)["value"]

    rows = [
        ("السعر · درهم", a["price"], b["price"], None),
        ("المحرك", cell(a, "المحرك"), cell(b, "المحرك"), None),
        ("القوة · حصان", cell(a, "القوة"), cell(b, "القوة"), None),
        ("ناقل الحركة", cell(a, "ناقل الحركة"), cell(b, "ناقل الحركة"), None),
        ("المنظومة", a["meta"][1], b["meta"][1], None),
        ("الموديل", cell(a, "الموديل"), cell(b, "الموديل"), None),
        ("تقييم أنوكار", a["rating"], b["rating"], "a"),
    ]
    tr = ""
    for k, va, vb, win in rows:
        ca = ' class="v win"' if win == "a" else ' class="v"'
        cb = ' class="v win"' if win == "b" else ' class="v"'
        tr += (f'<tr><td{ca}>{esc(va)}</td><td class="k">{esc(k)}</td><td{cb}>{esc(vb)}</td></tr>')
    return page("h2h", f'''
      {sec(H2H["kick"], "HEAD TO HEAD")}
      <h1 style="font-size:30pt;margin:4mm 0 3mm">{esc(H2H["title"])}</h1>
      <p class="stand" style="max-width:140mm">{esc(H2H["stand"])}</p>
      <div class="cars">
        <div class="car"><figure><img src="{a["img"]}"></figure>
          <h3>{esc(a["name_ar"])}</h3><div class="en">{esc(a["name_en"])}</div></div>
        <div class="car"><figure><img src="{b["img"]}"></figure>
          <h3>{esc(b["name_ar"])}</h3><div class="en">{esc(b["name_en"])}</div></div>
      </div>
      <div class="versus">وجهاً لوجه</div>
      <table><tbody>{tr}</tbody></table>''', H2H["kick"])


def h2h_verdict():
    a, b = by_en("Toyota Corolla"), by_en("BYD Qin Plus DM-i")
    escape = ""
    for src in (a, b):
        for alt in src["alternatives"][:2]:
            c = by_en(alt["name"].strip())
            if not c:
                continue
            escape += (f'<div><span class="en">{esc(c["name_en"])}</span>'
                       f'<b>{esc(c["price"])}</b>'
                       f'<u>{esc(c["meta"][1])} · صفحة {c["page"]}</u></div>')
    cons_a = next(s["value"] for s in a["specs"] if "الاستهلاك" in s["label"] or "المدى" in s["label"])
    cons_b = next(s["value"] for s in b["specs"] if "الاستهلاك" in s["label"] or "المدى" in s["label"])
    return page("h2h", f'''
      {sec(H2H["kick"], "THE VERDICT")}
      <h1 style="font-size:24pt;margin:4mm 0 4mm">الحكم يعتمد على مكان ركنك للسيارة</h1>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:7mm">
        <div><h3 style="font-family:'Display','AR';font-weight:800;font-size:14pt;margin-bottom:2.6mm">
            {esc(a["name_ar"])}</h3>
          <div class="cap" style="margin-bottom:3mm">{esc(cons_a)}</div>
          <p class="copy">{esc(H2H["verdict_a"])}</p></div>
        <div><h3 style="font-family:'Display','AR';font-weight:800;font-size:14pt;margin-bottom:2.6mm">
            {esc(b["name_ar"])}</h3>
          <div class="cap" style="margin-bottom:3mm">{esc(cons_b)}</div>
          <p class="copy">{esc(H2H["verdict_b"])}</p></div>
      </div>
      <div class="sidebar" style="margin-top:7mm"><h4>ما لا يظهر في الجدول</h4>
        <p>{esc(H2H["note"])}</p>
        <div class="row"><span>{esc(a["name_ar"])} — الحكم</span><b>{a["rating"]}</b></div>
        <div class="row"><span>{esc(b["name_ar"])} — الحكم</span><b>{b["rating"]}</b></div>
      </div>
      <div class="pull" style="margin-top:6mm"><p>الفارق بينهما ليس في الورق،
        بل في وجود مقبس كهرباء حيث تركن كل ليلة.</p></div>
      <h3 style="font-family:'Display','AR';font-weight:800;font-size:13pt;margin-bottom:3mm">
        وإذا كانت الميزانية أقل؟</h3>
      <div class="escape">{escape}</div>''', H2H["kick"])


# --------------------------------------------------------------- china feature
def china_a():
    ps = "".join(f"<p>{esc(p)}</p>" for p in CHINA["paras"])
    bins = [(30, 50), (50, 70), (70, 85), (85, 100)]
    rows = ""
    for lo, hi in bins:
        tot = [c for c in CARS if lo * 1000 <= c["low"] < hi * 1000]
        cn = [c for c in tot if c["meta"][0] == "الصين"]
        pct = len(cn) / len(tot) * 100 if tot else 0
        rows += (f'<div class="bar"><span>{num(f"{lo}–{hi}")} ألف درهم</span>'
                 f'<div class="track"><div class="fill" style="width:{pct:.0f}%;background:#D5301F">'
                 f'</div></div><span class="v">{len(cn)}/{len(tot)}</span></div>')
    return page("feat", f'''
      {sec(CHINA["kick"], "REPORT")}
      <h1 style="font-size:28pt;margin:4mm 0 3mm">{esc(CHINA["title"])}</h1>
      <p class="stand" style="max-width:140mm">{esc(CHINA["stand"])}</p>
      <div class="cols" style="margin-top:6mm">{ps}</div>
      <div style="margin-top:5mm">
        <h3 style="font-family:'AR';font-size:10pt;font-weight:600;margin-bottom:4mm">
          حصة العلامات الصينية داخل كل شريحة سعرية</h3>
        {rows}
        <div class="figcap"><b>الشكل 5</b> — عدد السيارات الصينية من إجمالي كل شريحة.
          الحضور يمتد من بوابة الدخول حتى ما يلامس السقف.</div>
      </div>
      <div class="pull" style="margin-top:6mm"><p>الفارق الذي لم يُغلق بعد اسمه ما بعد البيع.</p>
        <span>شبكة الخدمة · توفر القطع · قيمة إعادة البيع بعد ثلاث سنوات</span></div>''',
                CHINA["kick"])


def china_b():
    cn = sorted([c for c in CARS if c["meta"][0] == "الصين"], key=lambda c: c["low"])
    def table(part):
        rows = "".join(
            f'<tr><td class="car">{esc(c["name_en"])}</td>'
            f'<td class="pz">{esc(c["price"])}</td>'
            f'<td class="rt">{c["rating"] or "—"}</td>'
            f'<td class="pg">{c["page"]}</td></tr>' for c in part)
        return (f'<table class="itab"><thead><tr><th>السيارة</th><th>السعر</th><th>التقييم</th>'
                f'<th>صفحة</th></tr></thead><tbody>{rows}</tbody></table>')
    half = (len(cn) + 1) // 2
    items = "".join(f'<div class="row"><span>{esc(x)}</span></div>' for x in CHINA["side_items"])
    return page("feat", f'''
      {sec(CHINA["kick"], "REPORT")}
      <h1 style="font-size:20pt;margin:3mm 0 3mm">تسع وعشرون سيارة، من الأرخص إلى الأعلى</h1>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8mm">
        {table(cn[:half])}{table(cn[half:])}</div>
      <div class="sidebar" style="margin-top:6mm"><h4>{esc(CHINA["side_title"])}</h4>{items}</div>''',
                CHINA["kick"])


# ------------------------------------------------------------------- segments
def segments_page():
    panels = ""
    for k in ("entry", "daily", "family", "cap"):
        items = [c for c in CARS if c["seg"] == k]
        rated = [c for c in items if c["score"]]
        win = max(rated, key=lambda c: c["score"])
        cheap = min(items, key=lambda c: c["low"])
        panels += f'''<div class="seg" style="--seg:{SEG_COLOR[k]}">
          <h3>{esc(SEG_NAME[k])}</h3>
          <div class="meta">{len(items)} سيارة · {num(f'{min(c["low"] for c in items):,}')} –
            {num(f'{max(c["high"] for c in items):,}')} درهم</div>
          <figure><img src="{win["img"]}"></figure>
          <p>{esc(SEGMENTS["blurbs"][k])}</p>
          <div class="win"><b>الأعلى تقييماً:</b> {esc(win["name_ar"])} ({win["rating"]}) —
            صفحة {win["page"]}<br>
            <b>أرخص مدخل:</b> {esc(cheap["name_ar"])} عند {num(f'{cheap["low"]:,}')} درهم —
            صفحة {cheap["page"]}</div>
        </div>'''
    return page("feat", f'''
      {sec(SEGMENTS["kick"], "THE SEGMENTS")}
      <h1 style="font-size:28pt;margin:4mm 0 3mm">{esc(SEGMENTS["title"])}</h1>
      <p class="stand" style="max-width:140mm">{esc(SEGMENTS["stand"])}</p>
      <div class="segs">{panels}</div>''', SEGMENTS["kick"])


def decision_page():
    """Four reader profiles, answered from the data rather than from taste."""
    def top(pool, n=3):
        return sorted([c for c in pool if c["score"]], key=lambda c: -c["score"])[:n]

    profiles = [
        ("أول سيارة جديدة، والميزانية أقل من خمسين ألفاً",
         "أنت تشتري ضماناً وسنة صنع، لا تجهيزاً. تحقق من التأمين والصيانة قبل أن تحتفل بالسعر.",
         top([c for c in CARS if c["low"] < 50000])),
        ("تقود يومياً في المدينة وتستطيع الشحن في المنزل",
         "هنا وحدها يصبح الهجين القابل للشحن والكهربائي منطقيين. بلا مقبس ثابت، عد إلى البنزين.",
         top([c for c in CARS if c["meta"][1] != "بنزين"])),
        ("عائلة صغيرة وسفر منتظم بين الإمارات",
         "المقعد الخلفي والصندوق يقرران، لا الشكل. جرّب الجلوس في الخلف قبل التوقيع.",
         top([c for c in CARS if c["seg"] == "family"])),
        ("تريد أقصى ما يشتريه السقف",
         "أداء أعلى أو حجم أكبر أو اسم أقوى — وغالباً بلا هامش يُذكر تحت المئة ألف.",
         top([c for c in CARS if c["seg"] == "cap"])),
    ]
    blocks = ""
    for i, (q, note, picks) in enumerate(profiles, 1):
        cards = "".join(
            f'<div><figure><img src="{c["img"]}"></figure>'
            f'<span class="en">{esc(c["name_en"])}</span>'
            f'<b>{esc(c["price"])}</b>'
            f'<u>{c["rating"]} · صفحة {c["page"]}</u></div>' for c in picks)
        blocks += (f'<div class="prof"><div class="q"><span>{i:02d}</span>'
                   f'<div><h3>{esc(q)}</h3><p>{esc(note)}</p></div></div>'
                   f'<div class="picks">{cards}</div></div>')
    return page("feat", f'''
      {sec("من أين تبدأ؟", "WHERE TO START")}
      <h1 style="font-size:26pt;margin:4mm 0 3mm">أربعة أسئلة تختصر ثمانٍ وأربعين ملفاً</h1>
      <p class="stand" style="max-width:145mm">ابدأ من حالتك لا من القائمة. لكل حالة ثلاث سيارات
        هي الأعلى تقييماً داخل شروطها، ورقم صفحتها إلى جانبها.</p>
      <div class="profs">{blocks}</div>''', "من أين تبدأ؟")


# ------------------------------------------------------- buyer's guide (BOB)
def bob_open():
    t = BOB["title"].replace("\n", "<br>")
    hero = by_en("MG GT")
    key = ""
    for k in ("entry", "daily", "family", "cap"):
        items = [c for c in CARS if c["seg"] == k]
        lo = min(c["low"] for c in items)
        key += (f'<div style="border-top:3pt solid {SEG_COLOR[k]};padding-top:2.6mm">'
                f'<b>{esc(SEG_NAME[k])}</b>'
                f'<span>{len(items)} سيارة · من {num(f"{lo:,}")} درهم</span>'
                f'<u>الصفحات {items[0]["page"]} — {items[-1]["page"]}</u></div>')
    return page("opener flush", f'''
      <div class="bgshot"><img src="{hero["img"]}"></div>
      <div class="strip"><img src="{hero["img"]}"></div>
      <div class="scrim"></div>
      <div class="toplab">{esc(BOB["kick"])} · {ISSUE["brand"]} 01</div>
      <div class="txt"><div class="kick">{esc(BOB["kick"])}</div>
        <h1 style="font-size:46pt">{t}</h1><p>{esc(BOB["stand"])}</p>
        <div class="segkey">{key}</div>
        <div class="inthis">
          <div><span>لكل سيارة</span><b>ثمانية أرقام وحكم في سطرين</b></div>
          <div><span>الترتيب</span><b>من أرخص سعر دخول إلى أعلاه</b></div>
          <div><span>اللون</span><b>يحدد الشريحة السعرية</b></div>
        </div></div>''', folio=False)


def bg_entry(car, flip):
    seg = SEG_COLOR[car["seg"]]
    sp = ""
    for s in car["specs"][:8]:
        ar = re.search(r"[؀-ۿ]", s["value"])
        val = esc(s["value"]) if ar else num(esc(s["value"], False))
        sp += (f'<div>{esc(s["label"])}<b class="{"ar" if ar else ""}">{val}</b></div>')
    likes = "".join(f'<div>{esc(x)}</div>' for x in car["strengths"][:2])
    nos = "".join(f'<div class="no">{esc(x)}</div>' for x in car["caveats"][:2])
    alts = "، ".join(a["name"].strip() for a in car["alternatives"][:3])
    score = (f'<b>{car["rating"]}</b><span>من 10</span>' if car["rating"]
             else '<b style="font-size:10pt">—</b><span>إضافة محدَّثة</span>')
    upd = (f'<span class="upd">سعر محدَّث: {esc(car["price_updated"])}</span>'
           if car.get("price_updated") else "")
    return f'''<div class="bg-entry" style="--seg:{seg}">
      <div class="ph bleed"><img src="{car["img"]}">
        <div class="tag">{car["rank"]:02d} · {esc(car["meta"][0])} · {esc(SEG_NAME[car["seg"]])}</div>
        <div class="cr">{esc(car["credit"])}</div></div>
      <div class="txt">
        <div class="hd"><div><h3>{esc(car["name_ar"])}</h3>
            <span class="en">{esc(car["name_en"])}</span></div>
          <div class="price"><b>{esc(car["price"])}</b>
            <span>درهم · {esc(car["meta"][1])}</span>{upd}</div>
          <div class="sc">{score}</div></div>
        <div class="specs">{sp}</div>
        <div class="lower">
          <div class="say"><b>الحكم:</b> {esc(car["verdict"])}
            <div class="alt">بدائل مباشرة: <b>{esc(alts)}</b></div></div>
          <div class="pn">{likes}{nos}</div>
        </div>
      </div>
    </div>'''


def bg_pages():
    """Two cars a page, in price order, with a band whenever the segment changes."""
    pages = []
    cur_seg = None
    for i in range(0, len(CARS), 2):
        pair = CARS[i:i + 2]
        band = ""
        if pair[0]["seg"] != cur_seg:
            cur_seg = pair[0]["seg"]
            band = (f'<div class="segband" style="background:{SEG_COLOR[cur_seg]}">'
                    f'{esc(SEG_NAME[cur_seg])}</div>')
        entries = "".join(bg_entry(c, flip=False) for c in pair)
        pages.append((band, entries))
    return pages


# ---------------------------------------------------------------- back matter
def index_page(part, cars, note):
    rows = "".join(
        f'<tr><td class="n">{c["rank"]:02d}</td>'
        f'<td class="car">{esc(c["name_en"])}</td>'
        f'<td><span class="dot" style="background:{ORIGIN_COLOR.get(c["meta"][0], "#999")}"></span>'
        f'{esc(c["meta"][0])}</td>'
        f'<td>{esc(c["meta"][1])}</td>'
        f'<td class="pz">{esc(c["price"])}</td>'
        f'<td class="rt">{c["rating"] or "—"}</td>'
        f'<td class="pg">{c["page"]}</td></tr>' for c in cars)
    head = (f'<h1 style="font-size:24pt;margin:3mm 0 2mm">الفهرس الكامل</h1>'
            f'<p class="cap" style="font-size:8.4pt">كل السيارات مرتبة من أرخص سعر دخول '
            f'إلى أعلاه. رقم الصفحة يقود إلى الملف الكامل.</p>' if part == 1 else
            f'<h1 style="font-size:24pt;margin:3mm 0 2mm">الفهرس الكامل — تتمة</h1>')
    return page("index", f'''
      {sec("الفهرس", "INDEX")}{head}
      <table class="itab"><thead><tr><th>#</th><th>السيارة</th><th>المنشأ</th><th>المنظومة</th>
        <th>السعر (درهم)</th><th>التقييم</th><th>صفحة</th></tr></thead>
        <tbody>{rows}</tbody></table>{note}''', "الفهرس")


def brands_page():
    groups = {}
    for c in CARS:
        b = "Lynk & Co" if c["name_en"].startswith("Lynk") else c["name_en"].split()[0]
        groups.setdefault(b, []).append(c)
    html = ""
    for b in sorted(groups):
        items = sorted(groups[b], key=lambda c: c["low"])
        lis = "".join(
            f'<li><span class="en">{esc(c["name_en"].replace(b, "").strip() or b)}</span>'
            f'<b>{c["page"]}</b></li>' for c in items)
        html += f'<div class="brand"><h4>{esc(b)}</h4><ul>{lis}</ul></div>'
    o = counts(0)
    stats = "".join(f'<div><b>{v}</b><span>{esc(k)}</span></div>' for k, v in o.items())
    return page("index", f'''
      {sec("دليل العلامات", "BRANDS")}
      <h1 style="font-size:24pt;margin:3mm 0 2mm">دليل العلامات</h1>
      <p class="cap" style="font-size:8.4pt">{len(groups)} علامة داخل السقف.
        إذا كنت تعرف الاسم الذي تريده، ابدأ من هنا.</p>
      <div class="brands">{html}</div>
      <div class="stats" style="grid-template-columns:repeat(4,1fr)">{stats}</div>''',
                "دليل العلامات")


def close_page():
    steps = "".join(
        f'<div class="step"><span class="n">{i}</span><div><h3>{esc(t)}</h3><p>{esc(b)}</p></div></div>'
        for i, (t, b) in enumerate(CLOSE["steps"], 1))
    checks = "".join(f"<li>{esc(x)}</li>" for x in CLOSE["checks"])
    return page("steps", f'''
      {sec(CLOSE["kick"], "BEFORE YOU BUY")}
      <h1 style="font-size:30pt;margin:4mm 0 3mm">{esc(CLOSE["title"])}</h1>
      <p class="stand" style="max-width:140mm;margin-bottom:6mm">{esc(CLOSE["stand"])}</p>
      {steps}
      <div class="check"><h4>قائمة تحقق سريعة قبل التوقيع</h4><ul>{checks}</ul></div>''',
                CLOSE["kick"])


def colophon():
    return page("letter", f'''
      {sec("بيانات العدد", "MASTHEAD")}
      <h1 style="font-size:26pt;margin:4mm 0 3mm">{esc(ISSUE["title"])}</h1>
      <p class="stand" style="max-width:130mm">{esc(ISSUE["issue_line"])}</p>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:7mm 9mm;margin-top:8mm">
        <div class="rule-t" style="padding-top:3mm"><div class="cap">عدد السيارات</div>
          <div class="mono" style="font-size:13pt;margin-top:1.4mm">48</div>
          <p class="copy" style="font-size:8.4pt">41 مُقيَّمة و7 إضافات محدَّثة دخلت
            بعد إغلاق التقييم.</p></div>
        <div class="rule-t" style="padding-top:3mm"><div class="cap">النطاق السعري</div>
          <div class="mono" style="font-size:13pt;margin-top:1.4mm">{num("31,500 – 99,900")}</div>
          <p class="copy" style="font-size:8.4pt">درهم إماراتي، سعر الدخول لكل طراز.</p></div>
        <div class="rule-t" style="padding-top:3mm"><div class="cap">قطع البحث</div>
          <div class="mono" style="font-size:13pt;margin-top:1.4mm">{ISSUE["cutoff"]}</div>
          <p class="copy" style="font-size:8.4pt">كل رقم في هذا العدد يعود إلى هذا التاريخ.</p></div>
        <div class="rule-t" style="padding-top:3mm"><div class="cap">الإصدار</div>
          <div class="mono" style="font-size:13pt;margin-top:1.4mm">{ISSUE["version"]}</div>
          <p class="copy" style="font-size:8.4pt">{ISSUE["site"]}</p></div>
      </div>
      <div class="rulebox" style="margin-top:9mm">
        <div class="item"><b>01</b><div><h5>هيئة التحرير</h5>
          <p>بحث وتحرير: فريق أنوكار سوليوشنز · تصميم وإخراج: قسم النشر ·
             مراجعة الأسعار: مصادر الوكلاء داخل الدولة.</p></div></div>
        <div class="item"><b>02</b><div><h5>الصور</h5>
          <p>مواد رسمية من العلامات التجارية، تُستخدم للتعريف بالسيارة والجيل.
             حقوق الصور تعود لأصحابها.</p></div></div>
        <div class="item"><b>03</b><div><h5>إخلاء مسؤولية</h5>
          <p>{esc(ISSUE["disclaimer"])}</p></div></div>
      </div>
      <div class="cta" style="margin-top:8mm"><div><h3>{esc(CLOSE["cta_t"])}</h3>
        <p>{esc(CLOSE["cta_b"])}</p></div><div class="w">{ISSUE["brand"]}</div></div>''',
                "بيانات العدد")


GLOSSARY = [
    ("هجين (HEV)", "محرك بنزين وموتور كهربائي يشحن نفسه من الفرملة والمحرك. لا تحتاج مقبساً، "
                   "والفائدة تظهر في زحام المدينة أكثر من الطريق السريع."),
    ("هجين قابل للشحن (PHEV)", "بطارية أكبر تُشحن من الكهرباء، تمنح مدى كهربائياً يومياً ثم "
                               "يعمل البنزين بعده. جدواه مرتبطة بوجود مقبس ثابت."),
    ("CVT", "ناقل متغير باستمرار. سلس واقتصادي، لكن إحساس التسارع فيه مختلف عن الناقل التقليدي."),
    ("DCT", "ناقل بقابضين. أسرع في تبديل النسب، ويستحق تجربة في الزحام قبل الشراء."),
    ("NEDC / CLTC", "دورتا قياس مدى وكفاءة، الأرقام فيهما متفائلة مقارنة بالاستخدام الفعلي "
                    "في حرارة الخليج."),
    ("FWD", "دفع أمامي — الشائع في هذه الشريحة كلها."),
    ("سعر رسمي", "سعر معلن من وكيل مرخص داخل الدولة، ويشمل ضماناً معروف الشروط."),
    ("سعر استيراد", "سيارة تصل من خارج قنوات الوكيل. السعر أقل، والضمان والبرمجيات وقطع الغيار "
                    "تحتاج تحققاً منفصلاً."),
    ("مواصفات خليجية", "تجهيز تبريد وتكييف ومواصفات مطابقة لسوق المنطقة — بند يُسأل عنه كتابةً."),
    ("قيمة إعادة البيع", "ما يتبقى من سعرك بعد ثلاث سنوات. البند الذي لا يظهر في كتيّب "
                         "المواصفات ويظهر في محفظتك."),
]


def glossary_page():
    items = "".join(
        f'<div class="gl-item"><h4>{esc(t)}</h4><p>{esc(b)}</p></div>' for t, b in GLOSSARY)
    return page("index", f'''
      {sec("قاموس سريع", "GLOSSARY")}
      <h1 style="font-size:24pt;margin:3mm 0 2mm">عشرة مصطلحات تقرأها في كل ملف</h1>
      <p class="cap" style="font-size:8.4pt">ما تعنيه فعلياً للمشتري، لا ما يقوله الكتيّب.</p>
      <div class="gloss">{items}</div>''', "قاموس سريع")


def back_cover():
    hero = by_en("Honda Civic")
    line = BACK["line"].replace("\n", "<br>")
    return page("back flush", f'''
      <div class="bgshot"><img src="{hero["img"]}"></div>
      <div class="strip"><img src="{hero["img"]}"></div>
      <div class="scrim"></div>
      <div class="body"><div class="w">{ISSUE["brand"]}</div>
        <h2>{line}</h2>
        <div class="facts">
          <div><dt>عدد السيارات</dt><dd>48</dd></div>
          <div><dt>النطاق السعري</dt><dd>{num("31,500 – 99,900")}</dd></div>
          <div><dt>قطع البحث</dt><dd>{ISSUE["cutoff"]}</dd></div>
          <div><dt>الإصدار</dt><dd>{ISSUE["version"]}</dd></div>
        </div>
      </div>
      <div class="fine">{esc(BACK["fine"])}<span class="site">{ISSUE["site"]}</span></div>''',
                folio=False)


# --------------------------------------------------------------------- assemble
def main():
    # the running order is fixed, so every cross-reference can be resolved up front
    P_FRONT = 12                                  # cover .. group-test how-to
    P_RT = P_FRONT + 1                            # first road-test spread
    P_H2H = P_RT + len(FINALISTS) * 2             # head to head
    P_CHINA = P_H2H + 2
    P_SEG = P_CHINA + 2
    P_BOB = P_SEG + 2                             # buyer's guide opener
    P_GUIDE = P_BOB + 1
    n_guide = (len(CARS) + 1) // 2
    P_INDEX = P_GUIDE + n_guide
    P_BRANDS = P_INDEX + 2
    P_GLOSS = P_BRANDS + 1
    P_CLOSE = P_GLOSS + 1
    for i, c in enumerate(CARS):
        c["page"] = P_GUIDE + i // 2

    cover({"china": P_CHINA, "cheapest": CARS[0]["page"], "h2h": P_H2H,
           "group": P_FRONT - 1})
    PLAN["contents"] = len(PAGES) + 1
    contents({
        "features": [("Toyota Corolla", "الخمسة النهائيون", P_FRONT - 1),
                     ("BYD Qin Plus DM-i", "وجهاً لوجه: هجين أم قابل للشحن", P_H2H),
                     ("Geely Preface", "ملف العدد: معركة المئة ألف", 7),
                     ("Chery Arrizo 5", "دليل المشتري: 48 ملفاً", P_BOB)],
        "blocks": [
            ("الافتتاحية والمنهجية", [
                ("03", "مئة ألف درهم هي كل القصة", "افتتاحية العدد"),
                ("04", "كيف بُني هذا العدد", "أربع قواعد ورقم واحد"),
                ("05", "الرادار — أحد عشر رقماً", "ما يجب أن تعرفه أولاً"),
            ]),
            ("ملف العدد", [
                ("07", "معركة المئة ألف", "السوق تغيّر تحت أقدامنا"),
                ("09", "السوق بالأرقام", "أربعة رسوم تشرح السقف"),
                (f"{P_FRONT - 1}", "الخمسة النهائيون", "الاختبار الجماعي"),
                (f"{P_RT}", "خمسة ملفات كاملة", "من كورولا إلى سيتي"),
                (f"{P_H2H}", "هجين أم هجين قابل للشحن؟", "كورولا ضد تشين بلس"),
                (f"{P_CHINA}", "كيف غيّرت الصين قواعد الشريحة", "تحقيق"),
                (f"{P_SEG}", "أربع شرائح، أربعة قرارات", "خريطة الشرائح"),
            ]),
            ("دليل المشتري", [
                (f"{P_BOB}", "ثمانٍ وأربعون ملفاً", "من الأرخص إلى الأعلى"),
                (f"{P_INDEX}", "الفهرس الكامل", "48 صفاً في جدول واحد"),
                (f"{P_BRANDS}", "دليل العلامات", "25 علامة"),
                (f"{P_GLOSS}", "قاموس سريع", "عشرة مصطلحات"),
                (f"{P_CLOSE}", "قبل أن تشتري", "أربع خطوات وقائمة تحقق"),
            ]),
        ],
    })
    letter(); methodology(); radar_a(); radar_b()
    feature_open(); feature_text(); data_a(); data_b()
    group_open(); group_how()
    PLAN["road tests"] = len(PAGES) + 1
    for i, c in enumerate(FINALISTS, 1):
        road_test_photo(c, i); road_test_text(c, i)
    PLAN["head to head"] = len(PAGES) + 1
    h2h_page(); h2h_verdict()
    PLAN["china"] = len(PAGES) + 1
    china_a(); china_b()
    PLAN["segments"] = len(PAGES) + 1
    segments_page(); decision_page()
    PLAN["guide opener"] = len(PAGES) + 1
    bob_open()
    for band, entries in bg_pages():
        page("guide", f'{band}{entries}', "دليل المشتري")
    note1 = ('<div class="figcap" style="display:flex;gap:6mm;align-items:center">'
             + "".join(f'<span><span class="dot" style="background:{v}"></span>{esc(k)}</span>'
                       for k, v in ORIGIN_COLOR.items())
             + '<span style="margin-right:auto">النقطة تشير إلى منشأ العلامة لا بلد التجميع.</span></div>')
    note2 = ('<div class="figcap"><b>الشرطة (—)</b> تعني إضافة محدَّثة دخلت بعد إغلاق التقييم '
             'وتُقرأ كمرجع سعري. <b>السعر</b> نطاق يبدأ من أقل فئة مؤهلة داخل السقف وينتهي عند '
             'أعلى فئة رصدها البحث.</div>')
    PLAN["index"] = len(PAGES) + 1
    index_page(1, CARS[:24], note1); index_page(2, CARS[24:], note2)
    PLAN["brands"] = len(PAGES) + 1
    brands_page()
    PLAN["glossary"] = len(PAGES) + 1
    glossary_page()
    PLAN["close"] = len(PAGES) + 1
    close_page(); colophon(); back_cover()

    assert len(PAGES) % 4 == 0, f"{len(PAGES)} pages — a printed issue signs off in fours"
    for name, want in (("road tests", P_RT), ("head to head", P_H2H), ("china", P_CHINA),
                       ("segments", P_SEG), ("guide opener", P_BOB), ("index", P_INDEX),
                       ("brands", P_BRANDS), ("glossary", P_GLOSS), ("close", P_CLOSE)):
        got = PLAN.get(name)
        assert got is None or got == want, f"{name}: planned {want}, landed on {got}"

    outline = [[1, "الغلاف", 1], [1, "المحتويات", 2], [1, "الافتتاحية", 3],
               [1, "المنهجية", 4], [1, "الرادار", 5],
               [1, "ملف العدد — معركة المئة ألف", 7], [1, "السوق بالأرقام", 9],
               [1, "الاختبار الجماعي — الخمسة النهائيون", P_FRONT - 1]]
    for i, c in enumerate(FINALISTS, 1):
        outline.append([2, f'{i:02d} · {c["name_en"]} — {c["name_ar"]}', P_RT + (i - 1) * 2])
    outline += [[1, "وجهاً لوجه — كورولا ضد تشين بلس", P_H2H],
                [1, "تحقيق — كيف غيّرت الصين القواعد", P_CHINA],
                [1, "خريطة الشرائح", P_SEG], [1, "من أين تبدأ؟", P_SEG + 1],
                [1, "دليل المشتري", P_BOB]]
    for c in CARS:
        outline.append([2, f'{c["rank"]:02d} · {c["name_en"]} — {c["name_ar"]}', c["page"]])
    outline += [[1, "الفهرس الكامل", P_INDEX], [1, "دليل العلامات", P_BRANDS],
                [1, "قاموس سريع", P_GLOSS], [1, "قبل أن تشتري", P_CLOSE],
                [1, "بيانات العدد", P_CLOSE + 1], [1, "الغلاف الأخير", len(PAGES)]]
    (ROOT / "build" / "outline.json").write_text(
        json.dumps(outline, ensure_ascii=False), encoding="utf-8")

    html = (f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            f'<title>{ISSUE["brand"]} — {ISSUE["title"]}</title>'
            f'<link rel="stylesheet" href="../assets/magazine.css"></head><body>'
            f'{"".join(PAGES)}</body></html>')
    OUT.write_text(html, encoding="utf-8")
    print(f"pages={len(PAGES)}  guide starts at {CARS[0]['page']}  -> {OUT}")


if __name__ == "__main__":
    main()
