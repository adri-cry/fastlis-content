#!/usr/bin/env python3
"""Kill stale chrome-linux64 processes (own user only), keep this script alive."""
import os, signal, time

me = os.getpid()
killed = []
for pid in os.listdir('/proc'):
    if not pid.isdigit() or int(pid) == me:
        continue
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmd = f.read().replace(b'\0', b' ').decode(errors='ignore')
    except Exception:
        continue
    if 'chrome-linux64/chrome' in cmd and 'killchrome' not in cmd:
        try:
            os.kill(int(pid), signal.SIGKILL)
            killed.append((pid, cmd[:80]))
        except Exception as e:
            print(f"cant kill {pid}: {e}")
print(f"killed={len(killed)}")
for p, c in killed[:20]:
    print(p, c)
time.sleep(2)
remain = 0
for pid in os.listdir('/proc'):
    if not pid.isdigit():
        continue
    try:
        with open(f'/proc/{pid}/cmdline', 'rb') as f:
            cmd = f.read().replace(b'\0', b' ').decode(errors='ignore')
    except Exception:
        continue
    if 'chrome-linux64/chrome' in cmd:
        remain += 1
print(f"remaining={remain}")
