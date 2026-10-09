#!/usr/bin/env python3
"""Inject copy reels harian ke reels/index.html dari content/hari-ini.json.

Skema di hari-ini.json -> key "reels":
{
  "s1": {"kicker": "...", "h1": "teks <br> <span class=\\"blue\\">...</span>", "sub": "...", "bg": "assets/lab-06.jpg"},
  "s2": {"kicker": "...", "h1": "...", "sub": "...", "bg": "assets/lab-10.jpg"},
  "s3": {"title": "...", "sub": "...", "desc": "...", "bg": "assets/lab-07.jpg"},
  "s4": {"title": "...", "sub": "...", "desc": "...", "bg": "assets/lab-08.jpg"},
  "s5": {"title": "...", "sub": "...", "desc": "...", "bg": "assets/lab-09.jpg"},
  "s6": {"h1": "...", "sub": "...", "pills": ["a", "b", "c"]}
}
Semua field opsional kecuali yang dipakai template; yang kosong pakai template.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import BASE

JSON_P = os.path.join(BASE, "content", "hari-ini.json")
TPL = os.path.join(BASE, "reels", "template.html")
OUT = os.path.join(BASE, "reels", "index.html")


def set_inner(html, eid, new_inner):
    """Ganti innerHTML elemen ber-id eid. Return (html_baru, ketemu)."""
    pat = re.compile(
        r'(<[^>]*\bid="' + re.escape(eid) + r'"[^>]*>)(.*?)(</[^>]+>)',
        re.DOTALL)
    m = pat.search(html)
    if not m:
        return html, False
    return html[:m.start(2)] + new_inner + html[m.end(2):], True


def set_attr(html, eid, attr, val):
    pat = re.compile(
        r'(<[^>]*\bid="' + re.escape(eid) + r'"[^>]*\b' + attr + r'=")[^"]*(")',
    )
    m = pat.search(html)
    if not m:
        # coba tanpa attr yang sudah ada -> sisipkan sebelum >
        pat2 = re.compile(r'(<[^>]*\bid="' + re.escape(eid) + r'")([^>]*>)')
        m2 = pat2.search(html)
        if not m2:
            return html, False
        return (html[:m2.end(1)] + f' {attr}="{val}"' + html[m2.end(1):]), True
    return html[:m.start(2)] + val + html[m.end(2):], True


def main():
    j = json.load(open(JSON_P))
    r = j.get("reels")
    if not r:
        print("tidak ada key 'reels' di hari-ini.json -> index.html tidak diubah")
        return 0
    html = open(TPL).read()

    # scene 1 & 2: kicker/h1/sub (+ bg opsional)
    for s in ("s1", "s2"):
        d = r.get(s, {})
        for key, eid in (("kicker", f"{s}-k"), ("h1", f"{s}-h1"), ("sub", f"{s}-sub")):
            if d.get(key):
                html, ok = set_inner(html, eid, d[key])
                if not ok:
                    print(f"WARN: id {eid} tidak ketemu")
        if d.get("bg"):
            # ganti <img class="bg" src=...> di dalam div#sN, atau s2-dash img
            if s == "s2":
                html, _ = set_attr(html, "s2-dash", "data-bg", d["bg"])  # fallback di bawah
                # s2 pakai <div id="s2-dash"><img src=...>
                pat = re.compile(r'(<div[^>]*\bid="s2-dash"[^>]*>\s*<img[^>]*src=")[^"]*(")')
                html, n = pat.subn(r"\g<1>" + d["bg"] + r"\g<2>", html, count=1)
            else:
                pat = re.compile(
                    r'(<div[^>]*\bid="' + s + r'"[^>]*>\s*<img[^>]*class="bg"[^>]*src=")[^"]*(")')
                html, n = pat.subn(r"\g<1>" + d["bg"] + r"\g<2>", html, count=1)

    # scene 3-5: title/sub/desc (+ bg opsional)
    for s in ("s3", "s4", "s5"):
        d = r.get(s, {})
        for key, eid in (("title", f"{s}-t"), ("sub", f"{s}-sub"), ("desc", f"{s}-d")):
            if d.get(key):
                html, ok = set_inner(html, eid, d[key])
                if not ok:
                    print(f"WARN: id {eid} tidak ketemu")
        if d.get("bg"):
            pat = re.compile(
                r'(<div[^>]*\bid="' + s + r'"[^>]*>\s*<img[^>]*class="bg"[^>]*src=")[^"]*(")')
            html, n = pat.subn(r"\g<1>" + d["bg"] + r"\g<2>", html, count=1)

    # scene 6: h1/sub/pills
    d = r.get("s6", {})
    if d.get("h1"):
        html, _ = set_inner(html, "s6-h1", d["h1"])
    if d.get("sub"):
        html, _ = set_inner(html, "s6-sub", d["sub"])
    if d.get("pills"):
        pills = "".join(f'<span class="pill">{p}</span>' for p in d["pills"][:4])
        html, _ = set_inner(html, "s6-card", f'<div class="pill-row">{pills}</div>')

    open(OUT, "w").write(html)
    print("index.html ditulis dari template + copy reels hari ini")
    return 0


if __name__ == "__main__":
    sys.exit(main())
