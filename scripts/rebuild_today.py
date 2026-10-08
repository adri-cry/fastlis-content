#!/usr/bin/env python3
"""Render carousel produksi dari content/hari-ini.json + carousel/template.html. (v2: pakai _common)"""
import json
import os
import sys
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, screenshot

J = json.load(open(f"{BASE}/content/hari-ini.json"))
TPL = open(f"{BASE}/carousel/template.html").read()

slides = J["carousel"]
for i, s in enumerate(slides, start=1):
    h = TPL
    for k, v in s.items():
        h = h.replace("__" + k.upper() + "__", str(v))
    html = f"{BASE}/carousel/_slide{i}.html"
    open(html, "w").write(h)


def _one(i):
    html = f"{BASE}/carousel/_slide{i}.html"
    out = f"{BASE}/carousel/slide{i}.png"
    ok = screenshot(html, out)
    try:
        os.remove(html)
    except OSError:
        pass
    sz = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"slide{i} {'OK' if ok else 'FAIL'} {sz}", flush=True)
    return ok


if __name__ == "__main__":
    n = len(slides)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(_one, range(1, n + 1)))
    sys.exit(0 if all(results) else 1)
