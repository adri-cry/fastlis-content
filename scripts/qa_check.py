#!/usr/bin/env python3
"""QA otomatis: cek widow (baris terakhir 1 kata), placeholder sisa, ukuran file."""
import json, os, re, sys
BASE = os.environ.get("FASTLIS_BASE", os.path.expanduser("~/workspace/fastlis-content"))
J = json.load(open(f"{BASE}/content/hari-ini.json"))
issues = []
warns = []

def strip_tags(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&rarr;", ">").replace("&middot;", ".").replace("&#10003;", "V")
    return s.strip()

def check_widow(label, text):
    t = strip_tags(text)
    if not t:
        return
    # simulasi wrap kasar: judul Archivo ~76px di lebar 940px ≈ 12-14 kata/baris... pakai heuristik:
    words = t.split()
    # aturan: total kata yang kalau di-wrap manual pakai <br> aman; kalau tidak ada <br>,
    # flag jika kalimat > 8 kata tanpa jeda (rawan widow saat render)
    if "<br>" not in text and len(words) > 12:
        warns.append(f"{label}: kalimat panjang ({len(words)} kata) tanpa <br> manual — cek widow manual")

for i, s in enumerate(J["carousel"], start=1):
    for field in ("title", "body", "sticker", "caption", "note", "swipe"):
        v = s.get(field, "")
        if f"__{field.upper()}__" in v or "__" in v:
            issues.append(f"slide{i}.{field}: placeholder belum diganti: {v[:60]}")
        if field in ("title", "body"):
            check_widow(f"slide{i}.{field}", v)
    # foto harus ada
    photo = s.get("photo", "").replace("../html/", f"{BASE}/html/")
    if not os.path.exists(photo):
        issues.append(f"slide{i}.photo hilang: {s.get('photo')}")
    # output harus ada & >50KB
    out = f"{BASE}/carousel/slide{i}.png"
    if os.path.exists(out):
        sz = os.path.getsize(out)
        if sz < 50000:
            issues.append(f"slide{i}.png kekecilan ({sz}b), render mungkin gagal")
    else:
        warns.append(f"slide{i}.png belum dirender")

c = J.get("single", {})
for field in ("title", "sub", "sticker", "caption", "note"):
    v = c.get(field, "")
    if "__" in v:
        issues.append(f"single.{field}: placeholder belum diganti")
    if field in ("title", "sub"):
        check_widow(f"single.{field}", v)

# foto duplikat antar slide
seen = {}
for i, sl in enumerate(J["carousel"], start=1):
    ph = os.path.basename(sl.get("photo", ""))
    if ph:
        if ph in seen:
            issues.append(f"slide{i} & slide{seen[ph]}: foto sama ({ph}) - variasikan")
        else:
            seen[ph] = i

# caption IG maks 2200 karakter
for key in ("caption_carousel", "caption_single"):
    v = J.get(key, "")
    if len(v) > 2200:
        issues.append(f"{key}: {len(v)} karakter, melebihi batas IG 2200")

# slide terakhir wajib endcard branded
slides = J["carousel"]
if slides and slides[-1].get("variant") != "v-endcard":
    issues.append(f"slide{len(slides)}: variant harus v-endcard (slide penutup branded)")

# relevansi foto vs topik (pakai data/photo_tags.json)
import re as _re
try:
    _tags = json.load(open(os.path.join(BASE, "data", "photo_tags.json")))
    _topic_words = set(_re.findall(r"[a-z]+", J.get("topik", "").lower()))
    for i, sl in enumerate(slides, start=1):
        if sl.get("variant") == "v-endcard":
            continue  # foto endcard tidak ditampilkan
        ph = os.path.basename(sl.get("photo", ""))
        ptags = set(_tags.get(ph, []))
        # teks spesifik slide ini (bukan cuma topik global): judul+body+kicker+note
        slide_text = " ".join([sl.get("title", ""), sl.get("body", ""),
                               sl.get("kicker", ""), sl.get("note", ""),
                               sl.get("sticker", ""), J.get("topik", "")])
        words = set(_re.findall(r"[a-z]+", slide_text.lower()))
        # tolak foto non-lab untuk konten lab
        lab_words = ("lab", "qc", "analis", "westgard", "levey", "jennings",
                     "tabung", "sampel", "reagen", "klinik", "pasien", "patologi",
                     "analyzer", "mikroskop", "hematologi")
        if any(t == "bukan foto lab" for t in ptags) and any(lw in words for lw in lab_words):
            issues.append(f"slide{i}: foto {ph} BUKAN foto lab, tidak cocok untuk konten lab")
            continue
        ok = False
        for w in words:
            if len(w) < 4:
                continue
            for t in ptags:
                tnorm = t.replace(" ", "")
                if len(tnorm) < 4:
                    continue
                # prefix-4 matching: "analis" nyambung ke "analyzer"
                if w[:4] == tnorm[:4] or w in tnorm or tnorm in w:
                    ok = True
                    break
            if ok:
                break
        if not ok:
            issues.append(f"slide{i}: foto {ph} tidak nyambung dengan isi slide (tags: {sorted(ptags)[:4]})")
        # badge lingkaran cuma muat angka pendek
        badge = sl.get("badge", "")
        if badge and len(badge) > 3:
            issues.append(f"slide{i}: badge '{badge}' kepanjangan, isi angka saja (mis. '1')")
except Exception as e:
    issues.append(f"cek photo_tags gagal: {e}")

print(f"QA: {len(J['carousel'])} carousel + 1 single")
for w in warns:
    print("WARN:", w)
for e in issues:
    print("FAIL:", e)
if issues:
    print(f"\nQA GAGAL: {len(issues)} masalah")
    sys.exit(1)
print("\nQA LULUS" + (" (dengan warning, cek visual manual)" if warns else ""))
