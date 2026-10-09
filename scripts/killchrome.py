#!/usr/bin/env python3
"""Bersihkan proses Chrome headless nyangkut (milik user ini saja).

Hanya membunuh proses chrome yang headless (dipakai render), bukan semua
Chrome. Aman dipanggil sebelum/sesudah render.
"""
import os
import signal

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
    # hanya chrome headless (render), bukan chrome biasa
    if ('chrome' in cmd and '--headless' in cmd
            and 'killchrome' not in cmd and 'remote-debugging' not in cmd):
        try:
            os.kill(int(pid), signal.SIGKILL)
            killed.append(pid)
        except Exception as e:
            print(f"cant kill {pid}: {e}")
print(f"killed={len(killed)}")
