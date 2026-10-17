#!/usr/bin/env python3
"""Render reels via hyperframes dengan progress ke render_status.json.

Pakai:
  python3 scripts/render_reels.py --html v2/long.html --out v2/long_raw.mp4 --duration 115.3

Progress diestimasi dari durasi video (empiris render ~6x durasi video).
Dashboard membaca reels/v2/render_status.json (di-sync ke web) dan
menampilkan persentase render secara live.
"""
import argparse
import json
import os
import subprocess
import sys
import time

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
V2 = os.path.join(BASE, "reels", "v2")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_reels_whiteboard import write_status  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--factor", type=float, default=6.0,
                    help="estimasi waktu render = duration * factor")
    a = ap.parse_args()

    expected = max(30.0, a.duration * a.factor)
    t0 = time.time()
    write_status("render", 1, "render video dimulai")

    env = dict(os.environ)
    env["TMPDIR"] = os.path.join(BASE, "reels", ".tmp")
    os.makedirs(env["TMPDIR"], exist_ok=True)
    p = subprocess.Popen(
        ["npx", "hyperframes", "render", "-c", a.html, "-o", a.out],
        cwd=os.path.join(BASE, "reels"), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    last = 0
    while p.poll() is None:
        el = time.time() - t0
        prog = min(97.0, el / expected * 100)
        if time.time() - last > 5:
            write_status("render", prog,
                         f"merender video ({int(el)} dtk)")
            last = time.time()
        time.sleep(1)

    out = p.stdout.read() if p.stdout else ""
    if p.returncode != 0 or not os.path.exists(os.path.join(BASE, "reels", a.out)
                                               if not os.path.isabs(a.out) else a.out):
        write_status("error", 0, "render gagal: " + out[-300:])
        print("RENDER GAGAL:", out[-500:])
        return 1
    write_status("render-selesai", 100, "render selesai, siap mux")
    print(out.strip().splitlines()[-2:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
