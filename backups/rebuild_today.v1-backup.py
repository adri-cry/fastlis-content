#!/usr/bin/env python3
"""Render carousel produksi dari carousel/template.html (source of truth)."""
import os, subprocess
BASE = "/root/.fastlis-content"
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

slides = [
    dict(photo="../html/dashboard.webp", num="1 / 5", prog="20%", kicker="Kuis Validasi",
         title="Hasil kritis muncul. Siapa yang bertanggung jawab?",
         body="Tidak ada yang boleh mengirim hasil kritis tanpa tahu siapa yang memvalidasinya.", meta=""),
    dict(photo="../html/lab-01.jpg", num="2 / 5", prog="40%", kicker="Opsi A",
         title="Analisis validasi, lalu kirim langsung.",
         body="Validasi dilakukan analis senior, hasil langsung dikirim ke dokter.", meta=""),
    dict(photo="../html/lab-02.jpg", num="3 / 5", prog="60%", kicker="Opsi B",
         title="Patologi klinik review, lalu kirim.",
         body="Hasil kritis melewati patologi klinis sebelum dikirim ke dokter.", meta=""),
    dict(photo="../html/lab-03.jpg", num="4 / 5", prog="80%", kicker="Opsi C",
         title="Sistem kirim otomatis tanpa review.",
         body="Nilai kritis langsung dikirim, siapa pun yang login.", meta=""),
    dict(photo="../html/lab-04.jpg", num="5 / 5", prog="100%", kicker="Jawaban",
         title="B. Patologi klinik review, lalu kirim.",
         body="Validasi multi-level memastikan setiap hasil kritis diperiksa patologi klinis. Dokter menerima hasil yang sudah tervalidasi.", meta="Validasi multi-level · fastlis.com"),
]

for i, s in enumerate(slides, start=1):
    h = TPL.replace("__PHOTO__", s["photo"]).replace("__NUM__", s["num"]).replace("__PROGRESS__", s["prog"]).replace("__KICKER__", s["kicker"]).replace("__TITLE__", s["title"]).replace("__BODY__", s["body"]).replace("__META__", s["meta"])
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

import concurrent.futures
jobs = [(i, f"{BASE}/carousel/_slide{i}.html", f"{BASE}/carousel/slide{i}.png") for i in range(1, 6)]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    list(ex.map(_one, jobs))
