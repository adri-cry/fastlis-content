#!/usr/bin/env python3
"""Satu pintu: archive -> render carousel + single -> QA -> update tracking -> caption."""
import json, os, shutil, subprocess, datetime, sys
BASE = os.environ.get("FASTLIS_BASE", os.path.expanduser("~/workspace/fastlis-content"))

def run(cmd, label):
    print(f"\n=== {label} ===")
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=BASE)
    print(r.stdout.strip())
    if r.stderr.strip():
        print("STDERR:", r.stderr.strip()[-500:])
    return r.returncode == 0

# 1. archive output lama
today = datetime.date.today().isoformat()
dst = os.path.join(BASE, "archive", today)
os.makedirs(dst, exist_ok=True)
J = json.load(open(f"{BASE}/content/hari-ini.json"))
n = len(J.get("carousel", []))
targets = [f"carousel/slide{i}.png" for i in range(1, n+1)] + ["single/single-post.png"]
for t in targets:
    src = os.path.join(BASE, t)
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(dst, os.path.basename(t)))
        print("archived", t)
# prune >30 hari
cutoff = datetime.date.today() - datetime.timedelta(days=30)
for d in os.listdir(os.path.join(BASE, "archive")):
    p = os.path.join(BASE, "archive", d)
    if os.path.isdir(p) and d != "legacy":
        try:
            if datetime.date.fromisoformat(d) < cutoff:
                shutil.rmtree(p)
                print("pruned", d)
        except ValueError:
            pass

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
    if ph: photos.append(ph)
sp = os.path.basename(J.get("single", {}).get("photo", ""))
if sp: photos.append(sp)
used["last_run"] = today
used["today_carousel"] = [os.path.basename(s.get("photo","")) for s in J.get("carousel", [])]
used["today_single"] = [sp] if sp else []
used["used"] = sorted(set(used.get("used", [])) | set(photos))
json.dump(used, open(used_p, "w"), indent=2)
print("\nupdated used_images.json:", len(used["used"]), "foto terpakai")

hist_p = f"{BASE}/data/last_topics.json"
hist = json.load(open(hist_p))
hist.setdefault("history", [])
hist["history"] = [h for h in hist["history"] if h.get("date") != today]
hist["history"].append({"date": today, "topik": J.get("topik",""), "format": J.get("format","")})
hist["history"] = hist["history"][-30:]
json.dump(hist, open(hist_p, "w"), indent=2)
print("updated last_topics.json")

# 5. caption siap copy
print("\n=== CAPTION CAROUSEL (copy-paste) ===")
print(J.get("caption_carousel",""))
print("\n=== CAPTION SINGLE (copy-paste) ===")
print(J.get("caption_single",""))

print(f"\n=== SELESAI: carousel={'OK' if ok1 else 'FAIL'} single={'OK' if ok2 else 'FAIL'} qa={'OK' if ok3 else 'FAIL'} ===")
sys.exit(0 if (ok1 and ok2 and ok3) else 1)
