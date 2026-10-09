#!/usr/bin/env python3
"""Render carousel produksi dari content/hari-ini.json + carousel/template.html. (v2: pakai _common)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, screenshot_batch

J = json.load(open(f"{BASE}/content/hari-ini.json"))
TPL = open(f"{BASE}/carousel/template.html").read()

slides = J["carousel"]
for i, s in enumerate(slides, start=1):
    h = TPL
    for k, v in s.items():
        h = h.replace("__" + k.upper() + "__", str(v))
    html = f"{BASE}/carousel/_slide{i}.html"
    open(html, "w").write(h)


if __name__ == "__main__":
    n = len(slides)
    jobs = [(f"{BASE}/carousel/_slide{i}.html", f"{BASE}/carousel/slide{i}.png")
            for i in range(1, n + 1)]
    ok = screenshot_batch(jobs)
    for i in range(1, n + 1):
        try:
            os.remove(f"{BASE}/carousel/_slide{i}.html")
        except OSError:
            pass
    sys.exit(0 if ok else 1)
