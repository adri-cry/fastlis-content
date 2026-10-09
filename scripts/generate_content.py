#!/usr/bin/env python3
"""Generate content/hari-ini.json harian via LLM (Pollinations, gratis).

CATATAN: hanya alat bantu manual. Jadwal harian resmi memakai agen langsung
(lebih stabil) — lihat cron fastlis-daily-content.
"""
import datetime
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, wib_today

CONTENT = os.path.join(BASE, "content", "hari-ini.json")
HIST = os.path.join(BASE, "data", "last_topics.json")
USED = os.path.join(BASE, "data", "used_images.json")
HTMLDIR = os.path.join(BASE, "html")

API_URL = os.environ.get("FASTLIS_LLM_URL", "https://text.pollinations.ai/openai")
API_MODEL = os.environ.get("FASTLIS_LLM_MODEL", "openai")
MAX_RETRY = 3


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_json(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def photo_pool(used):
    exts = (".jpg", ".jpeg", ".png", ".webp")
    pool = sorted(f for f in os.listdir(HTMLDIR) if f.lower().endswith(exts))
    used_set = set(used.get("used", [])) | set(used.get("today_carousel", [])) | set(used.get("today_single", []))
    avail = [f for f in pool if f not in used_set]
    if len(avail) < 6:
        avail = pool
        used["used"] = []
    return avail


def build_prompt(history, photos):
    hist_txt = "\n".join(f"- {h.get('date')}: {h.get('topik')} [{h.get('format')}]" for h in history[-30:])
    photos_txt = ", ".join(photos)
    return f"""Kamu social media specialist untuk FastLIS, sistem informasi laboratorium (LIS) untuk analis kesehatan dan lab di Indonesia.

Buat SATU paket konten Instagram harian dalam Bahasa Indonesia yang santai tapi profesional, relate untuk analis lab / patologi klinik. Jangan pakai topik yang sudah pernah dipakai (lihat riwayat di bawah). Pilih salah satu format: kuis (jawaban di slide 5), before-vs-after, mitos-vs-fakta, tips praktis, atau checklist.

RIWAYAT TOPIK 30 HARI (jangan ulangi / jangan mirip):
{hist_txt if hist_txt else "(kosong)"}

FOTO TERSEDIA (wajib pakai format "../html/NAMAFILE", pilih yang cocok dengan topik, jangan pakai yang tidak ada di daftar):
{photos_txt}

KELUARKAN HANYA JSON valid (tanpa markdown fence, tanpa penjelasan), dengan struktur persis seperti ini:
{{
 "topik": "judul topik singkat",
 "format": "nama format",
 "date": "YYYY-MM-DD",
 "caption_carousel": "caption IG untuk carousel, 3-5 baris + hashtag relevan",
 "caption_single": "caption IG untuk single post + hashtag relevan",
 "carousel": [
  {{"badge": "", "badgeclass": "", "body": "1-2 kalimat", "caption": "kalimat pendek", "cta": "", "kicker": "kicker", "note": "catatan kecil", "num": "1/5", "photo": "../html/namafile.jpg", "prog": "20%", "sticker": "teks sticker", "swipe": "geser ...", "title": "judul, boleh pakai <br> dan <span class=\\"hl\\">", "variant": "v-cover"}},
  {{"badge": "A", "badgeclass": "", "body": "...", "caption": "...", "cta": "", "kicker": "Opsi A", "note": "...", "num": "2/5", "photo": "../html/namafile.jpg", "prog": "40%", "sticker": "...", "swipe": "...", "title": "...", "variant": "v-tilt"}},
  {{"badge": "B", "badgeclass": "", "body": "...", "caption": "...", "cta": "", "kicker": "Opsi B", "note": "...", "num": "3/5", "photo": "../html/namafile.jpg", "prog": "60%", "sticker": "...", "swipe": "...", "title": "...", "variant": "v-flip"}},
  {{"badge": "C", "badgeclass": "", "body": "...", "caption": "...", "cta": "", "kicker": "Opsi C", "note": "...", "num": "4/5", "photo": "../html/namafile.jpg", "prog": "80%", "sticker": "...", "swipe": "...", "title": "...", "variant": "v-tilt"}},
  {{"badge": "", "badgeclass": "", "body": "...", "caption": "...", "cta": "CTA misal: follow", "kicker": "Jawaban", "note": "...", "num": "5/5", "photo": "../html/namafile.jpg", "prog": "100%", "sticker": "...", "swipe": "", "title": "...", "variant": "v-cover"}}
 ],
 "single": {{"photo": "../html/namafile.jpg", "kicker": "...", "title": "...", "sub": "...", "meta": "...", "caption": "...", "sticker": "...", "note": "...", "cta": "..."}}
}}

Aturan: title/body jangan lebih dari 14 kata tanpa <br>; hindari placeholder "__"; ejaan Bahasa Indonesia yang benar; hashtag relevan (#fastlis #labindonesia dsb)."""


def call_llm(prompt):
    body = json.dumps({
        "model": API_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 6000,
        "private": True,
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        resp = json.load(r)
    return resp["choices"][0]["message"]["content"]


def extract_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def validate(j, history):
    errs = []
    for k in ("topik", "format", "caption_carousel", "caption_single", "carousel", "single"):
        if k not in j:
            errs.append(f"key hilang: {k}")
    car = j.get("carousel", [])
    if len(car) != 5:
        errs.append(f"carousel harus 5 slide, dapat {len(car)}")
    need_slide = ("badge", "badgeclass", "body", "caption", "cta", "kicker", "note",
                  "num", "photo", "prog", "sticker", "swipe", "title", "variant")
    for i, s in enumerate(car, 1):
        for k in need_slide:
            if k not in s:
                errs.append(f"slide{i} key hilang: {k}")
        ph = s.get("photo", "")
        if ph.startswith("../html/") and not os.path.exists(os.path.join(BASE, "html", ph.split("/")[-1])):
            errs.append(f"slide{i} foto tidak ada: {ph}")
        if "__" in json.dumps(s):
            errs.append(f"slide{i} masih ada placeholder __")
    need_single = ("photo", "kicker", "title", "sub", "meta", "caption", "sticker", "note", "cta")
    for k in need_single:
        if k not in j.get("single", {}):
            errs.append(f"single key hilang: {k}")
    nt = norm(j.get("topik", ""))
    for h in history:
        ht = norm(h.get("topik", ""))
        if nt and ht and (nt in ht or ht in nt or nt == ht):
            errs.append(f"topik mirip riwayat: {h.get('topik')}")
            break
    return errs


def main():
    today = wib_today().isoformat()
    hist = load_json(HIST, {}).get("history", [])
    used = load_json(USED, {"used": []})
    photos = photo_pool(used)
    json.dump(used, open(USED, "w"), indent=2)

    prompt = build_prompt(hist, photos)
    for attempt in range(1, MAX_RETRY + 1):
        print(f"generate attempt {attempt}/{MAX_RETRY} ...", flush=True)
        try:
            raw = call_llm(prompt)
            j = extract_json(raw)
            j["date"] = today
            errs = validate(j, hist)
            if not errs:
                if os.path.exists(CONTENT):
                    bak = os.path.join(BASE, "content", f"hari-ini.json.bak-{today}")
                    open(bak, "w").write(open(CONTENT).read())
                    print("backup:", bak)
                json.dump(j, open(CONTENT, "w"), indent=1, ensure_ascii=False)
                print(f"OK: topik = {j['topik']} [{j['format']}]")
                return 0
            print("validasi gagal:", "; ".join(errs[:5]))
        except Exception as e:
            print("error:", str(e)[:200])
    print("GAGAL generate konten setelah", MAX_RETRY, "percobaan")
    return 1


if __name__ == "__main__":
    sys.exit(main())
