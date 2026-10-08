#!/usr/bin/env python3
"""Render carousel produksi dari content/hari-ini.json + carousel/template.html."""
import json, os, subprocess
import concurrent.futures
BASE = "/root/.fastlis-content"
J = json.load(open(f"{BASE}/content/hari-ini.json"))
TPL = open(f"{BASE}/carousel/template.html").read()
CHROMES = [
    f"{os.path.expanduser('~')}/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome",
    "/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome",
    "/root/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome-headless-shell",
]

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

slides = J["carousel"]
for i, s in enumerate(slides, start=1):
    h = TPL
    for k, v in s.items():
        h = h.replace("__" + k.upper() + "__", v)
    html = f"{BASE}/carousel/_slide{i}.html"
    out = f"{BASE}/carousel/slide{i}.png"
    open(html, "w").write(h)

def _one(args):
    i, html, out = args
    ok = render(html, out)
    try:
        os.remove(html)
    except OSError:
        pass
    print(f"slide{i} {'OK' if ok else 'FAIL'} {os.path.getsize(out) if os.path.exists(out) else 0}", flush=True)
    return ok

if __name__ == "__main__":
    n = len(slides)
    jobs = [(i, f"{BASE}/carousel/_slide{i}.html", f"{BASE}/carousel/slide{i}.png") for i in range(1, n+1)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(_one, jobs))
