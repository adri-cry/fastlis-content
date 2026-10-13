#!/usr/bin/env python3
"""Reels FastLIS v2 full (36 dtk) sesuai style-spec.md:
- VO storyteller sebagai driver, subtitle karaoke word-highlight
- Kanvas navy gelap + drift kamera konstan, crossfade antar beat (no hard cut)
- Tiap beat WAJIB ada visual: foto polaroid / kartu data
- Chapter label mono, judul display bold, 3 warna
"""
import json
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(BASE, "vo_full.mp3")
OUT = os.path.join(BASE, "full.html")

BEATS = [
    {
        "label": "BAGIAN 01 &middot; HOOK",
        "title": 'SAMPEL PASIEN KAMU<br><span class="hl">PERNAH KETUKER?</span>',
        "visual": ("photo", "../assets/lab-08.jpg", "Tabung sampel pasien"),
        "text": "Coba bayangin. Sampel pasien kamu... pernah ketuker? "
                "Kedengerannya serem, tapi sering kejadian.",
    },
    {
        "label": "BAGIAN 02 &middot; KENAPA BISA",
        "title": 'PANGGIL NAMA DOANG,<br><span class="hl">LANGSUNG DIAMBIL.</span>',
        "visual": ("data", "RISIKO NYATA",
                   '2 nama sama<br><span class="hl">= 1 sampel tertukar</span>'),
        "text": "Penyebabnya: panggil nama doang, langsung diambil. "
                "Kalau ada dua pasien namanya sama? Wassalam. "
                "Sampel tertukar, hasil ikut salah.",
    },
    {
        "label": "BAGIAN 03 &middot; SOLUSI",
        "title": 'CEK 2 IDENTIFIER<br><span class="hl">DI BEDSIDE.</span>',
        "visual": ("photo", "../assets/lab-18.jpg", "Label ditempel di bedside"),
        "text": "Solusinya juga simpel. Cek dua identifier: nama lengkap dan "
                "tanggal lahir, cocokkan dengan gelang pasien. "
                "Tempel label di bedside, sebelum diambil, bukan di meja.",
    },
    {
        "label": "PENUTUP",
        "title": 'GELANG, FORM, LABEL.<br><span class="hl">BEDA SATU = STOP.</span>',
        "visual": ("ask", "Pernah kejadian di labmu?",
                   "Cerita di komentar."),
        "text": "Tiga titik: gelang, form, label. Beda satu, stop. "
                "Pernah kejadian di labmu? Cerita di komentar.",
    },
]


def audio_duration(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1", p],
        capture_output=True, text=True)
    return float(r.stdout.strip().split("=")[1])


def compute_timings(beats, total):
    words = []
    for bi, b in enumerate(beats):
        for w in b["text"].split(" "):
            words.append({"w": w, "bi": bi})
    weights = []
    for wd in words:
        wgt = len(wd["w"])
        if wd["w"].endswith("..."):
            wgt += 8
        elif wd["w"][-1] in ".?:":
            wgt += 4
        elif wd["w"][-1] == ",":
            wgt += 2
        weights.append(wgt)
    unit = total / sum(weights)
    t = 0.0
    for wd, wgt in zip(words, weights):
        wd["t0"] = round(t, 3)
        t += wgt * unit
        wd["t1"] = round(t, 3)
    bounds = []
    for bi in range(len(beats)):
        ws = [w for w in words if w["bi"] == bi]
        bounds.append((ws[0]["t0"], ws[-1]["t1"]))
    return words, bounds


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    dur = audio_duration(VO)
    total = round(dur + 0.4, 2)
    words, bounds = compute_timings(BEATS, dur)
    json.dump({"words": words, "bounds": bounds, "total": total},
              open(os.path.join(BASE, "timings_full.json"), "w"), indent=1)

    # karaoke spans per beat
    wi = 0
    karaoke_divs = []
    for bi, b in enumerate(BEATS):
        spans = []
        for w in b["text"].split(" "):
            spans.append(f'<span class="kw" id="w{wi}">{esc(w)}</span>')
            wi += 1
        karaoke_divs.append(
            f'<div class="phrase" id="p{bi}" style="display:none">'
            f'{" ".join(spans)}</div>')

    calls = []
    for i, wd in enumerate(words):
        calls.append(f'tl.call(setWord, [{i}], {wd["t0"]});')
    for bi, (a, b_) in enumerate(bounds):
        calls.append(f'tl.call(showPhrase, [{bi}], {a});')
    calls.append(f'tl.call(clearWords, [], {total - 0.05});')

    # beat divs + transisi
    beat_divs = []
    trans = []
    for bi, b in enumerate(BEATS):
        kind = b["visual"][0]
        if kind == "photo":
            _, src, cap = b["visual"]
            vis = (f'<div class="polaroid" id="b{bi}-vis">'
                   f'<div class="tape"></div>'
                   f'<img src="{src}">'
                   f'<div class="cap">{esc(cap)}</div></div>')
        elif kind == "data":
            _, cl, big = b["visual"]
            vis = (f'<div class="card" id="b{bi}-vis">'
                   f'<div class="cl">{cl}</div>'
                   f'<div class="big">{big}</div></div>')
        else:
            _, q, sub = b["visual"]
            vis = (f'<div class="card ask" id="b{bi}-vis">'
                   f'<div class="big">{esc(q)}</div>'
                   f'<div class="asksub">{esc(sub)}</div></div>')
        op = "" if bi == 0 else ' style="opacity:0"'
        beat_divs.append(
            f'<div class="beat" id="beat{bi}"{op}>'
            f'<div class="chlabel">{b["label"]}</div>'
            f'<div class="bigt">{b["title"]}</div>{vis}</div>')
        if bi > 0:
            t_in = round(bounds[bi][0] - 0.45, 2)
            trans.append(
                f'tl.to("#beat{bi-1}", {{opacity:0, y:-36, duration:.7, '
                f'ease:"power2.inOut"}}, {t_in});')
            trans.append(
                f'tl.fromTo("#beat{bi}", {{opacity:0, y:36}}, '
                f'{{opacity:1, y:0, duration:.7, ease:"power2.inOut"}}, {t_in});')
            trans.append(
                f'tl.from("#beat{bi} .chlabel", {{opacity:0, y:14, duration:.45}}, '
                f'{round(t_in + .15, 2)});')
            trans.append(
                f'tl.from("#beat{bi} .bigt", {{opacity:0, y:26, duration:.6}}, '
                f'{round(t_in + .3, 2)});')
            trans.append(
                f'tl.from("#b{bi}-vis", {{opacity:0, y:22, scale:.97, duration:.55}}, '
                f'{round(t_in + .55, 2)});')

    html = f"""<!doctype html>
<html lang="id">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<link href="../assets/fonts-poppins.css" rel="stylesheet">
<script src="../assets/gsap.min.js"></script>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{width:1080px;height:1920px;overflow:hidden;background:#071120}}
  body{{font-family:'Poppins',sans-serif}}
  #root{{width:1080px;height:1920px;position:relative;overflow:hidden;background:#071120}}
  #canvas{{position:absolute;inset:-70px;
    background:radial-gradient(rgba(120,175,230,.13) 2px, transparent 2.6px);
    background-size:36px 36px;}}
  #vignette{{position:absolute;inset:0;z-index:2;
    background:radial-gradient(ellipse 90% 70% at 50% 42%, transparent 40%, rgba(2,8,18,.80) 100%);}}
  .progress{{position:absolute;top:0;left:0;height:8px;width:0;background:#0469DC;z-index:5}}
  .beat{{position:absolute;inset:0;z-index:3;padding:110px 72px 0}}
  .chlabel{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:27px;
    letter-spacing:5px;color:#3B9EFF;font-weight:700}}
  .bigt{{font-size:86px;font-weight:800;color:#fff;line-height:1.04;
    letter-spacing:-2px;margin-top:24px;text-transform:uppercase}}
  .bigt .hl{{color:#3B9EFF}}
  .polaroid{{margin-top:40px;background:#fff;border-radius:10px;padding:18px 18px 0;
    transform:rotate(-2deg);box-shadow:0 24px 60px rgba(0,0,0,.45);position:relative}}
  .polaroid img{{width:100%;height:560px;object-fit:cover;display:block;border-radius:4px}}
  .polaroid .cap{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:26px;color:#334155;padding:18px 6px;letter-spacing:1px}}
  .polaroid .tape{{position:absolute;top:-22px;left:50%;width:180px;height:44px;
    background:rgba(230,236,245,.85);transform:translateX(-50%) rotate(3deg);
    border-left:2px dashed rgba(0,0,0,.12);border-right:2px dashed rgba(0,0,0,.12)}}
  .card{{margin-top:40px;background:rgba(10,22,40,.74);border:1px solid rgba(90,160,240,.30);
    border-radius:24px;padding:36px 38px}}
  .card .cl{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:24px;
    letter-spacing:4px;color:#3B9EFF;font-weight:700}}
  .card .big{{font-size:62px;font-weight:800;color:#fff;margin-top:12px;line-height:1.18}}
  .card .big .hl{{color:#3B9EFF}}
  .card.ask .big{{font-size:56px}}
  .card .asksub{{font-size:34px;color:rgba(255,255,255,.85);margin-top:14px;font-weight:600}}
  #karaoke{{position:absolute;left:56px;right:56px;bottom:110px;z-index:4;text-align:center}}
  .phrase{{display:inline-block;background:rgba(3,10,22,.68);border-radius:20px;
    padding:24px 32px;font-size:39px;font-weight:600;color:rgba(255,255,255,.93);
    line-height:1.5}}
  .kw{{transition:color .12s}}
  .kw.on{{color:#3B9EFF;font-weight:800}}
</style>
</head>
<body>
<div id="root" data-composition-id="full" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
  <div id="canvas"></div>
  <div id="vignette"></div>
  <div class="progress" id="prog"></div>
  {''.join(beat_divs)}
  <div id="karaoke">{''.join(karaoke_divs)}</div>
</div>
<script>
  var cur = -1, curP = -1;
  function setWord(i){{
    if(cur >= 0) document.getElementById('w'+cur).classList.remove('on');
    document.getElementById('w'+i).classList.add('on');
    cur = i;
  }}
  function clearWords(){{
    if(cur >= 0) document.getElementById('w'+cur).classList.remove('on');
    cur = -1;
  }}
  function showPhrase(p){{
    if(curP >= 0) document.getElementById('p'+curP).style.display = 'none';
    clearWords();
    document.getElementById('p'+p).style.display = 'inline-block';
    curP = p;
  }}
  var tl = gsap.timeline();
  tl.fromTo('#canvas', {{scale:1, x:0, y:0}}, {{scale:1.10, x:-30, y:-44, duration:{total}, ease:'none'}}, 0);
  tl.fromTo('#prog', {{width:0}}, {{width:1080, duration:{total}, ease:'none'}}, 0);
  tl.from('#beat0 .chlabel', {{opacity:0, y:16, duration:.5}}, .15);
  tl.from('#beat0 .bigt', {{opacity:0, y:30, duration:.7}}, .35);
  tl.from('#b0-vis', {{opacity:0, y:26, rotate:2, duration:.7}}, .8);
  {"".join(chr(10) + "  " + t for t in trans)}
  {"".join(chr(10) + "  " + c for c in calls)}
  tl.to({{}}, {{duration:{total}}});
</script>
</body>
</html>
"""
    open(OUT, "w").write(html)
    print(f"full.html ditulis, durasi {total}s, {len(words)} kata, "
          f"{len(bounds)} beat")


if __name__ == "__main__":
    main()
