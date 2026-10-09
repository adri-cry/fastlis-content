#!/usr/bin/env python3
"""Preview 1 slide tanpa render semua: preview.py <nomor_slide|single>

Contoh: python3 scripts/preview.py 1   -> render & tampilkan info slide1
        python3 scripts/preview.py single
Hasil PNG tetap di tempat biasa (carousel/slideN.png / single/single-post.png).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE, screenshot


def main():
    if len(sys.argv) < 2:
        print("pakai: preview.py <1..5|single>")
        return 2
    arg = sys.argv[1].lower()
    J = json.load(open(f"{BASE}/content/hari-ini.json"))
    if arg == "single":
        TPL = open(f"{BASE}/single/template.html").read()
        c = J["single"]
        mapping = {
            "__PHOTO__": c.get("photo", "../html/lab-05.jpg"),
            "__KICKER__": c.get("kicker", ""),
            "__TITLE__": c.get("title", ""),
            "__SUB__": c.get("sub", ""),
            "__META__": c.get("meta", ""),
            "__CAPTION__": c.get("caption", ""),
            "__STICKER__": c.get("sticker", ""),
            "__NOTE__": c.get("note", ""),
            "__CTA__": c.get("cta", ""),
        }
        h = TPL
        for k, v in mapping.items():
            h = h.replace(k, str(v))
        html, out = f"{BASE}/single/_preview.html", f"{BASE}/single/single-post.png"
    else:
        try:
            i = int(arg)
            assert 1 <= i <= len(J["carousel"])
        except (ValueError, AssertionError):
            print(f"nomor slide harus 1..{len(J['carousel'])} atau 'single'")
            return 2
        TPL = open(f"{BASE}/carousel/template.html").read()
        s = J["carousel"][i - 1]
        h = TPL
        for k, v in s.items():
            h = h.replace("__" + k.upper() + "__", str(v))
        html, out = f"{BASE}/carousel/_preview.html", f"{BASE}/carousel/slide{i}.png"
    open(html, "w").write(h)
    ok = screenshot(html, out)
    try:
        os.remove(html)
    except OSError:
        pass
    sz = os.path.getsize(out) if os.path.exists(out) else 0
    print(f"preview {'OK' if ok else 'FAIL'}: {out} ({sz} bytes)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
