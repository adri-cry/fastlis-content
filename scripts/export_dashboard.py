#!/usr/bin/env python3
"""Export data dashboard FastLIS -> JSON siap push ke artifact via invoke_action.
Pakai: python3 scripts/export_dashboard.py [--out FILE]
"""
import base64
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, wib_today

RENDERS = os.path.expanduser("~/workspace/fastlis-renders")

def thumb_b64(path, width=360):
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        r = width / im.width
        im = im.resize((width, int(im.height * r)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=68)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None

def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None

    hist = json.load(open(os.path.join(BASE, "data", "last_topics.json")))
    history = hist.get("history", [])

    # statistik format
    formats = {}
    for h in history:
        f = h.get("format", "?")
        formats[f] = formats.get(f, 0) + 1

    items = []
    for h in history[-14:]:
        d = h.get("date")
        rd = os.path.join(RENDERS, d)
        thumbs = []
        if os.path.isdir(rd):
            for i in range(1, 6):
                p = os.path.join(rd, f"slide{i}.png")
                if os.path.exists(p):
                    t = thumb_b64(p)
                    if t:
                        thumbs.append(t)
        items.append({
            "date": d,
            "topic": h.get("topik", ""),
            "format": h.get("format", ""),
            "cover": thumbs[0] if thumbs else None,
            "slide_count": len(thumbs),
            "has_reels": os.path.exists(os.path.join(rd, "fastlis-reels.mp4")),
        })

    # detail konten terbaru
    latest = None
    if history:
        d = history[-1]["date"]
        rd = os.path.join(RENDERS, d)
        slides = []
        single = None
        if os.path.isdir(rd):
            for i in range(1, 6):
                p = os.path.join(rd, f"slide{i}.png")
                if os.path.exists(p):
                    t = thumb_b64(p, width=540)
                    if t:
                        slides.append(t)
            sp = os.path.join(rd, "single.png")
            single = thumb_b64(sp, width=540) if os.path.exists(sp) else None
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
            "slides": slides,
            "single": single,
            "caption_carousel": cap_c,
            "caption_single": cap_s,
        }

    # 5 topik terakhir (penjaga anti-kembar)
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
