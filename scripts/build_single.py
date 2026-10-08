#!/usr/bin/env python3
"""Render single post produksi dari content/hari-ini.json + single/template.html."""
import json, os, subprocess
BASE = "/root/.fastlis-content"
J = json.load(open(f"{BASE}/content/hari-ini.json"))
TPL = open(f"{BASE}/single/template.html").read()
CHROMES = [
    f"{os.path.expanduser('~')}/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome",
    "/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome",
    "/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome-headless-shell",
]
c = J["single"]
mapping = {
    "__PHOTO__": c.get("photo","../html/lab-05.jpg"),
    "__KICKER__": c.get("kicker",""),
    "__TITLE__": c.get("title",""),
    "__SUB__": c.get("sub",""),
    "__META__": c.get("meta",""),
    "__CAPTION__": c.get("caption",""),
    "__STICKER__": c.get("sticker",""),
    "__NOTE__": c.get("note",""),
    "__CTA__": c.get("cta",""),
}
h = TPL
for k,v in mapping.items():
    h = h.replace(k, v)
html = f"{BASE}/single/_post.html"
out = f"{BASE}/single/single-post.png"
open(html, "w").write(h)

def render(html, out):
    for ch in CHROMES:
        if not os.path.exists(ch):
            continue
        try:
            r = subprocess.run([ch, "--headless=new", "--no-sandbox", "--disable-gpu",
                "--disable-dev-shm-usage", "--no-first-run", "--timeout=45000",
                "--hide-scrollbars", "--window-size=1080,1350",
                f"--screenshot={out}", f"file://{html}"],
                capture_output=True, text=True, timeout=120)
            if os.path.exists(out) and os.path.getsize(out) > 50000:
                return True
        except Exception:
            continue
    return False

ok = render(html, out)
print(f"single-post {'OK' if ok else 'FAIL'} {os.path.getsize(out) if os.path.exists(out) else 0}", flush=True)
try: os.remove(html)
except: pass
