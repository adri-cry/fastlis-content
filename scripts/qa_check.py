#!/usr/bin/env python3
"""QA otomatis: cek widow (baris terakhir 1 kata), placeholder sisa, ukuran file."""
import json, os, re, sys
BASE = "/root/.fastlis-content"
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

print(f"QA: {len(J['carousel'])} carousel + 1 single")
for w in warns:
    print("WARN:", w)
for e in issues:
    print("FAIL:", e)
if issues:
    print(f"\nQA GAGAL: {len(issues)} masalah")
    sys.exit(1)
print("\nQA LULUS" + (" (dengan warning, cek visual manual)" if warns else ""))
