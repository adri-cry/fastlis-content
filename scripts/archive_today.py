#!/usr/bin/env python3
"""Arsipkan output aktif ke archive/YYYY-MM-DD/ sebelum overwrite. Hapus arsip >30 hari."""
import os, shutil, datetime, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import wib_today
BASE = os.environ.get("FASTLIS_BASE", os.path.expanduser("~/workspace/fastlis-content"))
today = wib_today().isoformat()
dst = os.path.join(BASE, "archive", today)
os.makedirs(dst, exist_ok=True)
targets = [f"carousel/slide{i}.png" for i in range(1, 6)] + ["single/single-post.png", "reels/fastlis-reels.mp4"]
for t in targets:
    src = os.path.join(BASE, t)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(dst, os.path.basename(t)))
        print("archived", t)
cutoff = wib_today() - datetime.timedelta(days=30)
arch = os.path.join(BASE, "archive")
for d in os.listdir(arch):
    p = os.path.join(arch, d)
    if os.path.isdir(p) and d != "legacy":
        try:
            if datetime.date.fromisoformat(d) < cutoff:
                shutil.rmtree(p)
                print("pruned", d)
        except ValueError:
            pass
