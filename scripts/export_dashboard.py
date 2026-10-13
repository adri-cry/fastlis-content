#!/usr/bin/env python3
"""Export data dashboard FastLIS -> JSON dengan referensi URL media (bukan base64).

Media (slide PNG, single PNG, reels MP4) di-serve langsung oleh nginx dari
/srv/fastlis-dashboard/media/YYYY-MM-DD/. JSON hanya berisi path relatif.

Pakai: python3 scripts/export_dashboard.py [--out FILE]
Nama file single distandarisasi: single-post.png (fallback: single.png).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, wib_today

RENDERS = os.path.expanduser("~/workspace/fastlis-renders")
MEDIA_URL_PREFIX = "media"  # relatif terhadap root dashboard

SINGLE_NAMES = ("single-post.png", "single.png")  # urutan prioritas


def find_single(rd):
    for name in SINGLE_NAMES:
        p = os.path.join(rd, name)
        if os.path.exists(p):
            return name
    return None


def media_for(date):
    """Kembalikan dict media untuk tanggal tsb, path relatif atau None."""
    rd = os.path.join(RENDERS, date)
    slides = []
    if os.path.isdir(rd):
        for i in range(1, 6):
            name = f"slide{i}.png"
            if os.path.exists(os.path.join(rd, name)):
                slides.append(f"{MEDIA_URL_PREFIX}/{date}/{name}")
    single_name = find_single(rd) if os.path.isdir(rd) else None
    single = f"{MEDIA_URL_PREFIX}/{date}/{single_name}" if single_name else None
    reels = None
    if os.path.isdir(rd) and os.path.exists(os.path.join(rd, "fastlis-reels.mp4")):
        reels = f"{MEDIA_URL_PREFIX}/{date}/fastlis-reels.mp4"
    return {
        "slides": slides,
        "single": single,
        "reels": reels,
        "cover": slides[0] if slides else None,
        "slide_count": len(slides),
        "has_reels": reels is not None,
    }


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None

    hist = json.load(open(os.path.join(BASE, "data", "last_topics.json")))
    history = hist.get("history", [])

    formats = {}
    for h in history:
        f = h.get("format", "?")
        formats[f] = formats.get(f, 0) + 1

    items = []
    for h in history[-14:]:
        d = h.get("date")
        m = media_for(d)
        items.append({
            "date": d,
            "topic": h.get("topik", ""),
            "format": h.get("format", ""),
            "cover": m["cover"],
            "slide_count": m["slide_count"],
            "has_reels": m["has_reels"],
            "media": m,
        })

    latest = None
    if history:
        d = history[-1]["date"]
        m = media_for(d)
        cap_c = cap_s = ""
        jp = os.path.join(BASE, "content", "hari-ini.json")
        if os.path.exists(jp):
            j = json.load(open(jp))
            cap_c = j.get("caption_carousel", "")
            cap_s = j.get("caption_single", "")
        latest = {
            "date": d,
            "topic": history[-1].get("topik", ""),
            "format": history[-1].get("format", ""),
            "slides": m["slides"],
            "single": m["single"],
            "reels": m["reels"],
            "has_reels": m["has_reels"],
            "caption_carousel": cap_c,
            "caption_single": cap_s,
        }

    guard = [{"date": h.get("date"), "topic": h.get("topik", "")} for h in history[-5:]]

    payload = {
        "generated_at": wib_today().isoformat(),
        "stats": {
            "total_published": len(history),
            "formats": formats,
            "last_date": history[-1]["date"] if history else None,
        },
        "schedule": [
            {"name": "Konten gambar harian", "time": "06:14 WIB"},
            {"name": "Video reels harian", "time": "06:45 WIB"},
        ],
        "history": items,
        "latest": latest,
        "topic_guard": guard,
    }

    js = json.dumps(payload, ensure_ascii=False)
    if out:
        open(out, "w").write(js)
        print(f"dashboard JSON ditulis: {out} ({len(js)//1024} KB)")
    else:
        print(js)


if __name__ == "__main__":
    main()
