#!/usr/bin/env python3
"""Orkestrator harian fastlis-content (v2, alat bantu manual).

Urutan: generate konten -> render_all (arsip+render+QA+tracking) -> reels
(best-effort) -> git commit (+push bila FASTLIS_GITHUB_TOKEN diset).
Jadwal resmi memakai cron agen; script ini untuk run manual.
"""
import datetime
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE

LOGDIR = os.path.join(BASE, "logs")
os.makedirs(LOGDIR, exist_ok=True)
today = datetime.date.today().isoformat()
logf = open(os.path.join(LOGDIR, f"daily-{today}.log"), "a")


def log(msg):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    logf.write(line + "\n")
    logf.flush()


def run(cmd, label, cwd=BASE, timeout=900, check=True):
    log(f"=== {label}: {' '.join(cmd)} ===")
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.stdout.strip():
        for ln in r.stdout.strip().splitlines()[-25:]:
            logf.write("  | " + ln + "\n")
    if r.stderr.strip():
        logf.write("  STDERR: " + r.stderr.strip()[-800:] + "\n")
    logf.flush()
    ok = r.returncode == 0
    log(f"{label}: {'OK' if ok else f'GAGAL (rc={r.returncode})'}")
    if check and not ok:
        raise RuntimeError(f"{label} gagal")
    return ok


def main():
    py = sys.executable
    log(f"===== DAILY RUN {today} =====")
    try:
        run([py, "scripts/generate_content.py"], "GENERATE")
        run([py, "scripts/render_all.py"], "RENDER+QA")
    except RuntimeError as e:
        log(f"PIPELINE BERHENTI: {e}")
        return 1

    try:
        env = dict(os.environ, TMPDIR=os.path.join(BASE, "reels", ".tmp"))
        os.makedirs(env["TMPDIR"], exist_ok=True)
        run(["npm", "run", "render"], "REELS", cwd=os.path.join(BASE, "reels"),
            timeout=900, check=False)
    except Exception as e:
        log(f"reels skip: {e}")

    try:
        run(["git", "config", "user.name", "fastlis-bot"], "GIT CONFIG", check=False)
        run(["git", "config", "user.email", "fastlis-bot@local"], "GIT CONFIG", check=False)
        run(["git", "add", "-A"], "GIT ADD")
        st = subprocess.run(["git", "status", "--porcelain"], cwd=BASE,
                            capture_output=True, text=True)
        if st.stdout.strip():
            run(["git", "commit", "-m", f"content {today}"], "GIT COMMIT")
            token = os.environ.get("FASTLIS_GITHUB_TOKEN")
            if token:
                log("push ke GitHub ...")
                r = subprocess.run(
                    ["git", "-c", "http.extraHeader=Authorization: Bearer " + token,
                     "push", "origin", "main"],
                    cwd=BASE, capture_output=True, text=True, timeout=300)
                log(f"GIT PUSH: {'OK' if r.returncode == 0 else 'GAGAL: ' + r.stderr.strip()[-300:]}")
            else:
                log("FASTLIS_GITHUB_TOKEN tidak diset -> push dilewati (commit lokal saja)")
        else:
            log("tidak ada perubahan -> skip commit")
    except RuntimeError as e:
        log(f"git bermasalah (non-fatal): {e}")

    log(f"===== DAILY RUN {today} SELESAI =====")
    return 0


if __name__ == "__main__":
    rc = main()
    logf.close()
    sys.exit(rc)
