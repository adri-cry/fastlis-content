#!/usr/bin/env python3
"""Shared helpers untuk pipeline fastlis-content (v2).

- BASE bisa dioverride via env FASTLIS_BASE (default ~/workspace/fastlis-content;
  PENTING: hanya ~/ yang survive VM replace, jangan taruh di /root atau /tmp)
- Screenshot via Chrome DevTools Protocol (scripts/cdp_shot.py), bukan flag
  --screenshot (pernah gagal diam-diam = false positive).
"""
import os
import shutil
import subprocess

BASE = os.environ.get("FASTLIS_BASE", os.path.expanduser("~/workspace/fastlis-content"))


def find_chrome():
    cands = []
    env = os.environ.get("FASTLIS_CHROME")
    if env:
        cands.append(env)
    cands += [
        os.path.expanduser("~/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome"),
        "/opt/meta-chromium/chrome",
        "/opt/chrome/chrome-linux64/chrome",
    ]
    for c in cands:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    for name in ("google-chrome", "chromium", "chromium-browser"):
        p = shutil.which(name)
        if p:
            return p
    return None


def screenshot(html_path, out_path, width=1080, height=1350, min_bytes=50000):
    """Render file HTML lokal jadi PNG via CDP. Return True bila OK."""
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdp_shot.py")
    try:
        r = subprocess.run(
            [os.environ.get("FASTLIS_PYTHON", "python3"), helper,
             html_path, out_path, str(width), str(height)],
            capture_output=True, text=True, timeout=180)
        if r.stdout.strip():
            print(r.stdout.strip()[-200:])
        return r.returncode == 0 and os.path.exists(out_path) \
            and os.path.getsize(out_path) > min_bytes
    except Exception as e:
        print(f"screenshot gagal: {e}")
        return False
