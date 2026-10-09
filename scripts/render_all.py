#!/usr/bin/env python3
"""Satu pintu: archive -> render carousel + single -> QA -> update tracking -> caption."""
import datetime
import glob
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, wib_today, PipelineLock

today = wib_today().isoformat()


def run(cmd, label):
    print(f"\n=== {label} ===")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.stderr.strip():
        print("STDERR:", r.stderr.strip()[-500:])
    return r.returncode == 0


def main():
    with PipelineLock("render"):
        J = json.load(open(f"{BASE}/content/hari-ini.json"))

        # 1. archive output lama (satu implementasi: archive_today.py)
        ok0 = run([sys.executable, f"{BASE}/scripts/archive_today.py"], "ARCHIVE")

        # 2. render
        ok1 = run([sys.executable, f"{BASE}/scripts/rebuild_today.py"], "CAROUSEL")
        ok2 = run([sys.executable, f"{BASE}/scripts/build_single.py"], "SINGLE")

        # 3. QA
        ok3 = run([sys.executable, f"{BASE}/scripts/qa_check.py"], "QA")

        # 4. update tracking (foto + topik)
        used_p = f"{BASE}/data/used_images.json"
        used = json.load(open(used_p))
        photos = []
        for s in J.get("carousel", []):
            ph = os.path.basename(s.get("photo", ""))
            if ph:
                photos.append(ph)
        sp = os.path.basename(J.get("single", {}).get("photo", ""))
        if sp:
            photos.append(sp)
        used["last_run"] = today
        used["today_carousel"] = [os.path.basename(s.get("photo", "")) for s in J.get("carousel", [])]
        used["today_single"] = [sp] if sp else []
        used["used"] = sorted(set(used.get("used", [])) | set(photos))
        json.dump(used, open(used_p, "w"), indent=2)
        print("\nupdated used_images.json:", len(used["used"]), "foto terpakai")

        hist_p = f"{BASE}/data/last_topics.json"
        hist = json.load(open(hist_p))
        hist.setdefault("history", [])
        hist["history"] = [h for h in hist["history"] if h.get("date") != today]
        hist["history"].append({"date": today, "topik": J.get("topik", ""), "format": J.get("format", "")})
        hist["history"] = hist["history"][-30:]
        json.dump(hist, open(hist_p, "w"), indent=2)
        print("updated last_topics.json")

        # 4b. prune backup hari-ini.json.bak-* > 30 hari
        cutoff = wib_today() - datetime.timedelta(days=30)
        for bak in glob.glob(os.path.join(BASE, "content", "hari-ini.json.bak-*")):
            try:
                d = bak.rsplit("bak-", 1)[1]
                if datetime.date.fromisoformat(d) < cutoff:
                    os.remove(bak)
                    print("pruned backup", os.path.basename(bak))
            except (ValueError, IndexError):
                pass

        # 5. caption siap copy
        print("\n=== CAPTION CAROUSEL (copy-paste) ===")
        print(J.get("caption_carousel", ""))
        print("\n=== CAPTION SINGLE (copy-paste) ===")
        print(J.get("caption_single", ""))

        print(f"\n=== SELESAI: carousel={'OK' if ok1 else 'FAIL'} single={'OK' if ok2 else 'FAIL'} qa={'OK' if ok3 else 'FAIL'} ===")
        return 0 if (ok0 and ok1 and ok2 and ok3) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        print(f"BATAL: {e}")
        sys.exit(2)
