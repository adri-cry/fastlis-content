#!/usr/bin/env python3
"""Shared helpers untuk pipeline fastlis-content (v2).

- BASE bisa dioverride via env FASTLIS_BASE (default ~/workspace/fastlis-content;
  PENTING: hanya ~/ yang survive VM replace, jangan taruh di /root atau /tmp)
- Screenshot via Chrome DevTools Protocol (scripts/cdp_shot.py), bukan flag
  --screenshot (pernah gagal diam-diam = false positive).
"""
import datetime
import fcntl
import os
import shutil
import subprocess

BASE = os.environ.get("FASTLIS_BASE", os.path.expanduser("~/workspace/fastlis-content"))

try:
    from zoneinfo import ZoneInfo
    _WIB = ZoneInfo("Asia/Jakarta")
except Exception:
    _WIB = None


def wib_now():
    """Waktu sekarang zona WIB. Semua penanggalan pipeline pakai ini,
    bukan waktu sistem (UTC) — cron jalan 06:14 WIB = 23:14 UTC kemarin."""
    if _WIB:
        return datetime.datetime.now(_WIB)
    return datetime.datetime.utcnow() + datetime.timedelta(hours=7)


def wib_today():
    return wib_now().date()


class PipelineLock:
    """File lock biar tidak ada 2 run jalan bareng (jadwal vs manual)."""

    def __init__(self, name="pipeline"):
        self.path = os.path.join(BASE, f".lock-{name}")
        self.fh = None

    def __enter__(self):
        self.fh = open(self.path, "w")
        try:
            fcntl.flock(self.fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.fh.close()
            self.fh = None
            raise RuntimeError("pipeline sedang jalan (lock aktif), batalkan run ini")
        self.fh.write(str(os.getpid()))
        self.fh.flush()
        return self

    def __exit__(self, *a):
        try:
            if self.fh:
                fcntl.flock(self.fh, fcntl.LOCK_UN)
                self.fh.close()
        finally:
            try:
                os.remove(self.path)
            except OSError:
                pass


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


def screenshot_batch(jobs, width=1080, height=1350):
    """Banyak capture dalam SATU Chrome (jauh lebih cepat dari 1 Chrome per gambar).

    jobs: list of (html_path, out_path). Return True bila semua OK.
    """
    import json as _json
    import tempfile
    helper = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cdp_shot.py")
    spec = [{"html": h, "out": o, "width": width, "height": height} for h, o in jobs]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        _json.dump(spec, f)
        jf = f.name
    try:
        r = subprocess.run(
            [os.environ.get("FASTLIS_PYTHON", "python3"), helper, "--batch", jf],
            capture_output=True, text=True, timeout=600)
        if r.stdout.strip():
            print(r.stdout.strip()[-600:])
        return r.returncode == 0
    except Exception as e:
        print(f"screenshot_batch gagal: {e}")
        return False
    finally:
        try:
            os.remove(jf)
        except OSError:
            pass


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
