#!/usr/bin/env python3
"""Extract structured content + imagery from the AnoKar source guide PDF.

The source PDF stores Arabic as pre-shaped presentation forms in visual order,
so every string is NFKC-normalised back to base letters and the bidi artefacts
(leading punctuation, orphaned tashkeel) are repaired before use.
"""
import json, re, sys, unicodedata as ud
from pathlib import Path
import pymupdf
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "build" / "source.pdf"
IMG = ROOT / "assets" / "img"
OUT = ROOT / "build" / "content.json"

ARABIC_LETTER = re.compile(r"[\u0620-\u064A\u066E-\u06D3\u06FA-\u06FF]")


def _dir(ch: str) -> str:
    """Bidi class, coarse: R = Arabic letter, L = Latin/digit, N = neutral."""
    cat = ud.category(ch)
    if cat == "Mn":                       # tashkeel rides on the letter before it
        return "M"
    if cat == "Nd" or (cat.startswith("L") and ord(ch) < 0x0590):
        return "L"
    if ARABIC_LETTER.match(ch):
        return "R"
    return "N"                            # spaces, ، ؛ ؟ · — ( ) . and friends


def fix(text: str) -> str:
    """Rebuild logical order from the source PDF's visual-order text.

    PyMuPDF un-reverses the letters inside each strong run but leaves the runs
    themselves — and the neutrals sitting between them — in visual (left to
    right) order. Reversing the run sequence puts the line back the way it was
    typed; neutrals *inside* a run are already correct and stay put.
    """
    s = ud.normalize("NFKC", text)
    if not s.strip():
        return ""
    orphan_marks, head, i = "", [], 0      # tashkeel stranded at the visual edge
    while i < len(s) and _dir(s[i]) in ("N", "M"):
        (orphan_marks := orphan_marks + s[i]) if _dir(s[i]) == "M" else head.append(s[i])
        i += 1
    s = "".join(head) + s[i:]

    chunks = []
    for ch in s:
        d = _dir(ch)
        if chunks and (d == "M" or chunks[-1][0] == d):
            chunks[-1][1] += ch
        else:
            chunks.append([d, ch])

    merged = []
    for i, (d, t) in enumerate(chunks):
        if d == "N" and merged and i + 1 < len(chunks):
            prev, nxt = merged[-1][0], chunks[i + 1][0]
            if prev == nxt and prev != "N":       # neutral inside a run: leave it
                merged[-1][1] += t
                continue
        if d != "N" and merged and merged[-1][0] == d:
            merged[-1][1] += t
            continue
        merged.append([d, t])

    MIRROR = str.maketrans("()[]{}<>", ")(][}{><")
    # two sentence marks stacked at the visual edge: the first one closes the
    # sentence that ends on the Latin run, the second closes the line
    extra_stop = False
    if merged and merged[0][0] == "N" and merged[0][1].strip() == "..":
        merged[0][1], extra_stop = ".", True

    out = ""
    for d, t in reversed(merged):
        t = t.strip().translate(MIRROR) if d == "N" else t.strip()
        if not t:
            continue
        glue = not out or out.endswith("\u0640") or (d == "N" and t[0] in ".،؛:!؟%)»]")
        out += ("" if glue else " ") + t
        if extra_stop and d == "L":
            out, extra_stop = out + ".", False
    out = re.sub(r"\s+", " ", out).strip()
    if orphan_marks:
        idx = max((i for i, c in enumerate(out) if ARABIC_LETTER.match(c)), default=-1)
        out = out[:idx + 1] + orphan_marks + out[idx + 1:] if idx >= 0 else out + orphan_marks
    return out


# spec labels arrive with the numeric/parenthetical parts flipped; map to canon
SPEC_LABELS = {
    "المحرك": "المحرك",
    "(القوة )حصان": "القوة",
    "(العزم )نيوتن.م": "العزم",
    "كم/س100–0": "0–100 كم/س",
    "0–100 كم/س": "0–100 كم/س",
    "ناقل الحركة": "ناقل الحركة",
    "نظام الدفع": "نظام الدفع",
    "الاستهلاك": "الاستهلاك",
    "الموديل": "الموديل",
    "(البطارية )ك.و.س": "البطارية",
    "(المدى )كم": "المدى",
}
SPEC_UNITS = {
    "القوة": "حصان",
    "العزم": "نيوتن·م",
    "0–100 كم/س": "ثانية",
    "البطارية": "ك.و.س",
    "المدى": "كم",
}


def ascending(s: str) -> str:
    """A numeric range that came out high-to-low was reversed with its line."""
    def swap(m):
        a, b = m.group(1), m.group(2)
        try:
            if float(a.replace(",", "")) > float(b.replace(",", "")):
                return f"{b} – {a}"
        except ValueError:
            pass
        return m.group(0)
    return re.sub(r"([\d][\d.,]*)\s*[–—-]\s*([\d][\d.,]*)", swap, s)


# the source generator draws bracketed asides as a detached "( )" pair, which no
# generic reordering can put back — these seven cells are corrected by hand
PAREN_FIXES = {
    "55 – 128 كم كهربائي ( CLTC)": "55 – 128 كم كهربائي (CLTC)",
    "116 أساسي) (": "116 (أساسي)",
    "150 أساسي) (": "150 (أساسي)",
    "1.5L / 1.5T حسب المرجع) (": "1.5L / 1.5T (حسب المرجع)",
    "15.6 كم/لتر )مرجع سوقي)": "15.6 كم/لتر (مرجع سوقي)",
    "NEDC 350–380 كم )تقديري / ) 442 كم": "350–380 كم NEDC (تقديري) / 442 كم",
    "حتى 40 كم/لتر )مرجع سوقي / ) EV ~125 كم": "حتى 40 كم/لتر (مرجع سوقي) / ~125 كم EV",
}


def spans(page):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for line in b["lines"]:
            for sp in line["spans"]:
                t = sp["text"]
                if not t.strip():
                    continue
                out.append({
                    "raw": ud.normalize("NFKC", t).strip(),
                    "text": fix(t),
                    "x0": sp["bbox"][0], "x1": sp["bbox"][2], "y": sp["bbox"][1],
                    "size": round(sp["size"], 1),
                    "font": sp["font"].split("+")[-1],
                })
    return out


# one bullet carries two sentence marks that reordering cannot place on its own
TEXT_FIXES = {
    "غير مُدرجة في تقييم الإصدار 01 طابق الفئة على أرض المعرض.؛":
        "غير مُدرجة في تقييم الإصدار 01؛ طابق الفئة على أرض المعرض.",
}


def wrap_join(lines):
    """One bullet per source line — except where a long bullet wrapped, which is
    recognisable because the first line does not close its sentence."""
    lines = [TEXT_FIXES.get(x, x) for x in lines]
    out = []
    for line in lines:
        if out and not re.search(r"[.؟!]$", out[-1]):
            out[-1] = f"{out[-1]} {line}"
        else:
            out.append(line)
    return out


def anchor(sp_list, needle, default=None):
    for s in sp_list:
        if s["text"] == needle:
            return s["y"]
    return default


def parse_car(page, page_no):
    sp = spans(page)
    car = {"source_page": page_no}

    for s in sp:
        if s["font"].endswith("Mono-Bold") and re.fullmatch(r"\d+ / 48", s["raw"]):
            car["rank"] = int(s["raw"].split("/")[0])
        elif s["font"].endswith("SansArabic-Bold") and s["size"] > 20:
            car["name_ar"] = s["text"]
        elif s["font"].endswith("Serif-Regular") and 10 <= s["size"] <= 12 and "name_en" not in car:
            car["name_en"] = s["raw"]
        elif s["font"].endswith("SansArabic") and "·" in s["text"] and s["size"] == 9.0 and "meta" not in car:
            car["meta"] = [p.strip() for p in s["text"].split("·")]

    rating = [s for s in sp if s["y"] < 160 and re.fullmatch(r"\d+\.\d+", s["raw"])]
    car["rating"] = rating[0]["raw"] if rating else None   # unrated entries show an em dash

    price = [s for s in sp if 230 < s["y"] < 300 and s["font"].endswith("Mono-Bold")]
    car["price"] = price[0]["raw"] if price else None
    upd = [s for s in sp if 230 < s["y"] < 300 and s["font"].endswith("Mono-Regular")
           and s["size"] >= 12]
    car["price_updated"] = upd[0]["raw"] if upd else None

    y_specs = anchor(sp, "الأرقام", 320)
    y_str = anchor(sp, "نقاط القوة", 494)
    y_verdict = anchor(sp, "رأي المحرر", 546)
    y_fit = anchor(sp, "مناسبة لـ", 631)
    y_pos = anchor(sp, "موقع السعر داخل السقف", 653)
    y_next = anchor(sp, "اجلس في هذه بعدها", 711)

    # ---- spec grid: label spans (8.2) with the value span sitting just below
    labels = [s for s in sp if y_specs < s["y"] < y_str - 5 and s["size"] == 8.2]
    values = [s for s in sp if y_specs < s["y"] < y_str - 5 and s["size"] >= 9.5]
    specs = []
    for lab in sorted(labels, key=lambda s: (round(s["y"]), -s["x1"])):
        cand = [v for v in values if 4 < v["y"] - lab["y"] < 18
                and not (v["x1"] < lab["x0"] - 4 or v["x0"] > lab["x1"] + 40)]
        if not cand:
            continue
        val = min(cand, key=lambda v: abs(v["x1"] - lab["x1"]))
        values.remove(val)
        key = SPEC_LABELS.get(lab["raw"], fix(lab["raw"]))
        raw_val = ascending(val["text"] if re.search(r"[؀-ۿ]", val["raw"]) else val["raw"])
        clean = raw_val.strip(" –-") or "—"
        specs.append({"label": key, "value": PAREN_FIXES.get(clean, clean),
                      "unit": SPEC_UNITS.get(key, "")})
    car["specs"] = specs

    # ---- two bullet columns: strengths (right/first column) vs caveats (left)
    bullets = [s for s in sp if y_str < s["y"] < y_verdict - 5 and "Light" in s["font"]]
    car["strengths"] = wrap_join([s["text"] for s in sorted(
        [b for b in bullets if b["x1"] > 320], key=lambda s: s["y"])])
    car["caveats"] = wrap_join([s["text"] for s in sorted(
        [b for b in bullets if b["x1"] <= 320], key=lambda s: s["y"])])

    verdict = [s["text"] for s in sorted(
        [s for s in sp if y_verdict < s["y"] < y_fit - 6 and "Light" in s["font"]],
        key=lambda s: s["y"])]
    car["verdict"] = join_ar(verdict)

    fit = [s["text"] for s in sp if abs(s["y"] - y_fit) < 8 and "Light" in s["font"]]
    car["fit"] = fit[0] if fit else ""

    # ---- "sit in these next": Latin name + price + page reference
    alts = []
    for s in sp:
        if y_next < s["y"] < y_next + 30 and s["font"].endswith("Serif-Regular"):
            near = [t for t in sp if abs(t["x0"] - s["x0"]) < 30 and 6 < t["y"] - s["y"] < 20
                    and t["font"].endswith("Mono-Regular")]
            alts.append({"name": s["raw"].strip(), "price": near[0]["raw"] if near else ""})
    car["alternatives"] = alts

    credit = [s["text"] for s in sp if "الصورة:" in s["text"]]
    car["credit"] = credit[0] if credit else ""
    return car


def join_ar(parts):
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def extract_images(doc):
    """Pull the one hero photo carried by each car page; keep the largest."""
    mapping = {}
    for pno in range(len(doc)):
        imgs = doc[pno].get_images(full=True)
        if not imgs:
            continue
        imgs = sorted(imgs, key=lambda i: i[2] * i[3], reverse=True)
        for idx, info in enumerate(imgs):
            xref = info[0]
            pix = pymupdf.Pixmap(doc, xref)
            if pix.colorspace and pix.colorspace.n > 3:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            name = f"p{pno+1:02d}" + (f"_{idx}" if len(imgs) > 1 else "") + ".jpg"
            # JPEG keeps the 64-page PDF in the megabytes rather than tens of them
            Image.frombytes("RGB", (pix.width, pix.height), pix.samples).save(
                IMG / name, "JPEG", quality=86, optimize=True, progressive=True)
            mapping.setdefault(pno + 1, []).append(name)
    return mapping


def main():
    doc = pymupdf.open(SRC)
    images = extract_images(doc)
    cars = []
    for pno in range(7, 55):          # pages 8..55 hold one car each
        car = parse_car(doc[pno], pno + 1)
        car["image"] = (images.get(pno + 1) or [None])[0]
        cars.append(car)
    data = {
        "cars": cars,
        "cover_image": (images.get(1) or [None])[0],
        "opener_image": (images.get(7) or [None])[0],
        "picks_images": images.get(56, []),
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"cars={len(cars)} images={sum(len(v) for v in images.values())} -> {OUT}")
    bad = [c for c in cars if not c.get("name_en") or not c.get("specs")]
    print("incomplete:", [c["source_page"] for c in bad])


if __name__ == "__main__":
    main()
