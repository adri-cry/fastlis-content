#!/usr/bin/env python3
"""Render single post produksi dari content/hari-ini.json + single/template.html. (v2: pakai _common)"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, screenshot

J = json.load(open(f"{BASE}/content/hari-ini.json"))
TPL = open(f"{BASE}/single/template.html").read()
c = J["single"]
mapping = {
    "__PHOTO__": c.get("photo", "../html/lab-05.jpg"),
    "__KICKER__": c.get("kicker", ""),
    "__TITLE__": c.get("title", ""),
    "__SUB__": c.get("sub", ""),
    "__META__": c.get("meta", ""),
    "__CAPTION__": c.get("caption", ""),
    "__STICKER__": c.get("sticker", ""),
    "__NOTE__": c.get("note", ""),
    "__CTA__": c.get("cta", ""),
}
h = TPL
for k, v in mapping.items():
    h = h.replace(k, str(v))
html = f"{BASE}/single/_post.html"
out = f"{BASE}/single/single-post.png"
open(html, "w").write(h)

ok = screenshot(html, out)
sz = os.path.getsize(out) if os.path.exists(out) else 0
print(f"single-post {'OK' if ok else 'FAIL'} {sz}", flush=True)
try:
    os.remove(html)
except OSError:
    pass
sys.exit(0 if ok else 1)
