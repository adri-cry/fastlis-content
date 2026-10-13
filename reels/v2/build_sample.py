#!/usr/bin/env python3
"""Sampel 15 detik reels FastLIS gaya sinematik v2 (referensi: video @SATYAXBT).
- Voice over AI (vo_sample.mp3) sebagai driver
- Subtitle karaoke: kata yang diucapkan menyala biru
- Satu kanvas gelap + kamera drift pelan, tanpa potongan kasar
- Label chapter mono + judul besar
"""
import json, os, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
VO = os.path.join(BASE, "vo_sample.mp3")
OUT = os.path.join(BASE, "sample.html")

# naskah VO, dipecah jadi frasa untuk subtitle
PHRASES = [
    "Coba bayangin.",
    "Sampel pasien kamu... pernah ketuker?",
    "Kedengerannya serem, tapi ini sering kejadian.",
    "Penyebabnya simpel: panggil nama doang, langsung diambil.",
    "Kalau ada dua pasien namanya sama? Wassalam.",
]

def audio_duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=noprint_wrappers=1", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip().split("=")[1])

def compute_timings(phrases, total):
    words = []
    for pi, ph in enumerate(phrases):
        for w in ph.split(" "):
            words.append({"w": w, "pi": pi})
    # bobot: panjang kata + jeda tanda baca
    weights = []
    for i, wd in enumerate(words):
        wgt = len(wd["w"])
        if wd["w"].endswith("..."):
            wgt += 8   # jeda dramatis
        elif wd["w"][-1] in ".?:":
            wgt += 4   # jeda akhir kalimat
        elif wd["w"][-1] == ",":
            wgt += 2
        weights.append(wgt)
    unit = total / sum(weights)
    t = 0.0
    for wd, wgt in zip(words, weights):
        wd["t0"] = round(t, 3)
        t += wgt * unit
        wd["t1"] = round(t, 3)
    # rentang tiap frasa
    prange = []
    for pi in range(len(phrases)):
        ws = [w for w in words if w["pi"] == pi]
        prange.append((ws[0]["t0"], ws[-1]["t1"]))
    return words, prange

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def main():
    dur = audio_duration(VO)
    total = round(dur + 0.4, 2)  # sedikit ekor
    words, prange = compute_timings(PHRASES, dur)
    json.dump({"words": words, "phrases": prange, "total": total},
              open(os.path.join(BASE, "timings.json"), "w"), indent=1)

    # bangun span karaoke per frasa
    wi = 0
    phrase_html = []
    for pi, ph in enumerate(PHRASES):
        spans = []
        for w in ph.split(" "):
            spans.append(f'<span class="kw" id="w{wi}">{esc(w)}</span>')
            wi += 1
        phrase_html.append(
            f'<div class="phrase" id="p{pi}" style="display:none">{" ".join(spans)}</div>')

    # pemetaan kata -> (t0) untuk GSAP calls
    calls = []
    for i, wd in enumerate(words):
        calls.append(f'tl.call(setWord, [{i}], {wd["t0"]});')
    for pi, (a, b) in enumerate(prange):
        calls.append(f'tl.call(showPhrase, [{pi}], {a});')
    calls.append(f'tl.call(clearWords, [], {total - 0.05});')
    calls_js = "\n    ".join(calls)

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
  #canvas{{position:absolute;inset:-60px;
    background:
      radial-gradient(rgba(120,175,230,.13) 2px, transparent 2.6px);
    background-size:36px 36px;}}
  #vignette{{position:absolute;inset:0;z-index:2;
    background:radial-gradient(ellipse 90% 70% at 50% 42%, transparent 40%, rgba(2,8,18,.78) 100%);}}
  .progress{{position:absolute;top:0;left:0;height:8px;width:0;background:#0469DC;z-index:5}}
  .scene{{position:absolute;inset:0;z-index:3;padding:120px 72px 0}}
  .chlabel{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:27px;
    letter-spacing:5px;color:#3B9EFF;font-weight:700}}
  .bigt{{font-size:92px;font-weight:800;color:#fff;line-height:1.02;
    letter-spacing:-2px;margin-top:26px;text-transform:uppercase}}
  .bigt .hl{{color:#3B9EFF}}
  .card{{margin-top:44px;background:rgba(10,22,40,.72);border:1px solid rgba(90,160,240,.28);
    border-radius:24px;padding:34px 36px;backdrop-filter:blur(6px)}}
  .card .cl{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:24px;
    letter-spacing:4px;color:#3B9EFF;font-weight:700}}
  .card .big{{font-size:64px;font-weight:800;color:#fff;margin-top:12px;line-height:1.15}}
  .card .big .hl{{color:#3B9EFF}}
  #karaoke{{position:absolute;left:56px;right:56px;bottom:110px;z-index:4;text-align:center}}
  .phrase{{display:inline-block;background:rgba(3,10,22,.66);border-radius:20px;
    padding:26px 34px;font-size:41px;font-weight:600;color:rgba(255,255,255,.92);
    line-height:1.5}}
  .kw{{transition:color .12s}}
  .kw.on{{color:#3B9EFF;font-weight:800}}
  #sB{{opacity:0}}
</style>
</head>
<body>
<div id="root" data-composition-id="sample" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
  <div id="canvas"></div>
  <div id="vignette"></div>
  <div class="progress" id="prog"></div>

  <div class="scene" id="sA">
    <div class="chlabel">BAGIAN 01 &middot; PRE-ANALITIK</div>
    <div class="bigt">Sampel pasien kamu<br><span class="hl">pernah ketuker?</span></div>
  </div>

  <div class="scene" id="sB">
    <div class="chlabel">BAGIAN 02 &middot; KENAPA BISA</div>
    <div class="bigt">Panggil nama doang,<br><span class="hl">langsung diambil.</span></div>
    <div class="card">
      <div class="cl">RISIKO NYATA</div>
      <div class="big">2 pasien, 1 nama<br><span class="hl">= sampel tertukar</span></div>
    </div>
  </div>

  <div id="karaoke">
    {''.join(phrase_html)}
  </div>
</div>
<script>
  var NWORDS = {len(words)};
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
  // kamera drift pelan sepanjang video
  tl.fromTo('#canvas', {{scale:1, x:0, y:0}}, {{scale:1.09, x:-24, y:-34, duration:{total}, ease:'none'}}, 0);
  tl.fromTo('#prog', {{width:0}}, {{width:1080, duration:{total}, ease:'none'}}, 0);
  // scene A masuk
  tl.from('#sA .chlabel', {{opacity:0, y:16, duration:.5}}, .15);
  tl.from('#sA .bigt', {{opacity:0, y:30, duration:.7}}, .35);
  // transisi ke scene B (tanpa potongan kasar: crossfade + geser)
  tl.to('#sA', {{opacity:0, y:-40, duration:.8, ease:'power2.inOut'}}, 7.6);
  tl.fromTo('#sB', {{opacity:0, y:40}}, {{opacity:1, y:0, duration:.8, ease:'power2.inOut'}}, 7.7);
  tl.from('#sB .card', {{opacity:0, y:24, duration:.6}}, 8.6);
  // karaoke
  {calls_js}
  tl.to({{}}, {{duration:{total}}});
</script>
</body>
</html>
"""
    open(OUT, "w").write(html)
    print(f"sample.html ditulis, durasi {total}s, {len(words)} kata")

if __name__ == "__main__":
    main()
