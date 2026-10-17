#!/usr/bin/env python3
"""Prototipe reels gaya WHITEBOARD (hand-drawn) untuk penilaian Adri.
Topik: delta check. Bukan kuis. Output: reels/v2/whiteboard.html + vo + timings.
"""
import json, os, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(BASE, "reels", "v2")
sys.path.insert(0, os.path.join(BASE, "scripts"))
from build_reels_whiteboard import (real_word_timings, audio_duration, esc,
                            TTS, VOICE)

BEATS = [
    {"narr": "Hasil lab hari ini beda jauh dari kemarin? Jangan langsung rilis.",
     "scene": 0},
    {"narr": "Namanya delta check. Bandingkan hasil baru dengan hasil kunjungan sebelumnya.",
     "scene": 1},
    {"narr": "Contoh, kalium pasien 4,1 minggu lalu, sekarang 6,5. Jauh banget kan?",
     "scene": 2},
    {"narr": "Aturannya mudah. Kalau lewat batas delta, tahan dulu dan validasi ulang.",
     "scene": 3},
    {"narr": "Follow FastLIS untuk edukasi lab setiap hari.",
     "scene": 4},
]

# ---------------- 1. TTS ----------------
narr_text = "\n".join(b["narr"] for b in BEATS)
vo_path = os.path.join(V2, "vo_whiteboard.mp3")
open(os.path.join(V2, "vo_whiteboard.txt"), "w").write(narr_text)
cp = subprocess.run([TTS, "speak", "--language", "id", "--voice", VOICE,
                     "--output", vo_path, "--text-stdin"],
                    input=narr_text.encode(), capture_output=True)
if cp.returncode != 0 or not os.path.exists(vo_path):
    print("TTS GAGAL:", cp.stderr.decode()[:500]); sys.exit(1)
dur = audio_duration(vo_path)
total = round(dur + 0.6, 2)
print(f"VO jadi: {dur:.1f}s, total render {total}s")

# ---------------- 2. timings ----------------
words, bounds = [], []
try:
    allw = [w for b in BEATS for w in b["narr"].split(" ")]
    rt = real_word_timings(vo_path, allw)
    t = 0.0
    for bi, b in enumerate(BEATS):
        ws = b["narr"].split(" ")
        t0 = t
        for j, w in enumerate(ws):
            words.append({"w": w, "t0": round(rt[len(words)], 3)})
        # akhir beat = t0 kata terakhir + estimasi durasi kata
        t1 = rt[len(words) - 1] + 0.45
        bounds.append((round(t0, 3), round(t1, 3)))
        t = t1 + 0.15
    print(f"timing karaoke: REAL (whisper, {len(words)} kata)")
except Exception as e:
    print(f"whisper gagal ({e}), pakai estimasi proporsional")
    t = 0.0
    for bi, b in enumerate(BEATS):
        ws = b["narr"].split(" ")
        bd = dur * len(" ".join(ws)) / max(1, len(narr_text.replace("\n", " ")))
        for j, w in enumerate(ws):
            words.append({"w": w, "t0": round(t + bd * j / len(ws), 3)})
        bounds.append((round(t, 3), round(t + bd, 3)))
        t += bd + 0.15

json.dump({"words": words, "bounds": bounds, "total": total},
          open(os.path.join(V2, "timings_whiteboard.json"), "w"), indent=1)

# ---------------- 3. HTML ----------------
wi = 0
karaoke_divs = []
for bi, b in enumerate(BEATS):
    spans = [f'<span class="kw" id="w{wi + j}">{esc(w)}</span>'
             for j, w in enumerate(b["narr"].split(" "))]
    wi += len(spans)
    karaoke_divs.append(
        f'<div class="phrase" id="p{bi}" style="display:none">{" ".join(spans)}</div>')

calls = [f'tl.call(setWord, [{i}], {wd["t0"]});' for i, wd in enumerate(words)]
for bi, (a, _) in enumerate(bounds):
    calls.append(f'tl.call(showPhrase, [{bi}], {a});')
    calls.append(f'tl.call(showScene, [{BEATS[bi]["scene"]}], {a});')
calls.append(f'tl.call(clearWords, [], {total - 0.05});')
calls_js = "\n    ".join(calls)

scene_btn = [bounds[i][0] for i in range(5)]

html = f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'Caveat'; src:url('../assets/fonts/caveat-700.woff2') format('woff2'); font-weight:700; }}
@font-face {{ font-family:'Poppins'; src:url('../assets/fonts/poppins-6.woff2') format('woff2'); font-weight:600; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
#root {{ width:1080px; height:1920px; position:relative; overflow:hidden;
  background:#FBF9F4; font-family:'Caveat',cursive; color:#1a1a1a; }}
#root::before {{ content:''; position:absolute; inset:0;
  background-image:radial-gradient(#00000008 1px, transparent 1px);
  background-size:28px 28px; }}
.scene {{ position:absolute; inset:0; display:none; padding:40px 70px 300px 70px; }}
.scene.on {{ display:flex; flex-direction:column; }}
.scene.on > *:first-child {{ margin-top:auto; }}
.scene.on > *:last-child {{ margin-bottom:auto; }}
.ink {{ stroke:#1a1a1a; stroke-width:7; fill:none; stroke-linecap:round; stroke-linejoin:round; }}
.ink-red {{ stroke:#E23B3B; stroke-width:9; fill:none; stroke-linecap:round; }}
.ink-blue {{ stroke:#1B5FD9; stroke-width:7; fill:none; stroke-linecap:round; }}
.draw {{ stroke-dasharray:1; stroke-dashoffset:1; }}
h1.hand {{ font-size:110px; line-height:1.05; text-align:center; }}
h1.hand .hl {{ background:linear-gradient(transparent 8%, #FFE45E 8%, #FFE45E 92%, transparent 92%); padding:0 14px; }}
h1.hand .blue {{ color:#1B5FD9; }}
.sub {{ font-family:'Poppins',sans-serif; font-size:34px; color:#555; text-align:center; margin-top:18px; }}
.card-paper {{ background:#fff; border:5px solid #1a1a1a; border-radius:18px;
  box-shadow:6px 6px 0 #1a1a1a22; padding:34px 30px; text-align:center; }}
.bignum {{ font-size:150px; line-height:1; }}
.lbl {{ font-family:'Poppins',sans-serif; font-size:30px; letter-spacing:3px; color:#777; }}
.stickrow {{ display:flex; justify-content:center; gap:40px; margin-top:30px; }}
.check {{ display:flex; align-items:center; gap:26px; margin:26px 40px; font-size:64px; }}
.pill {{ display:inline-block; border:5px solid #1a1a1a; border-radius:999px;
  padding:18px 54px; font-size:56px; background:#fff; box-shadow:5px 5px 0 #1a1a1a22; }}
/* karaoke */
#karaoke {{ position:absolute; left:60px; right:60px; bottom:90px; min-height:190px;
  display:flex; align-items:center; justify-content:center; text-align:center; }}
.phrase {{ font-family:'Poppins',sans-serif; font-weight:600; font-size:44px; line-height:1.5; color:#1a1a1a; }}
.kw {{ padding:2px 8px; border-radius:8px; transition:background .12s; }}
.kw.on {{ background:#FFE45E; }}
#brand {{ position:absolute; top:56px; left:70px; font-family:'Poppins',sans-serif;
  font-weight:800; font-size:34px; letter-spacing:2px; }}
#brand b {{ color:#1B5FD9; }}
</style></head>
<body>
<div id="root" data-composition-id="whiteboard" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
<div id="brand">FAST<b>LIS</b></div>

<!-- filter wobble tangan -->
<svg width="0" height="0"><defs>
<filter id="wobble"><feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="2" result="n"/>
<feDisplacementMap in="SourceGraphic" in2="n" scale="7"/></filter>
</defs></svg>

<!-- SCENE 0 : hook -->
<div class="scene" id="s0">
  <h1 class="hand">Hasil beda jauh<br><span class="hl">dari kemarin?</span></h1>
  <div class="stickrow">
    <div class="card-paper"><div class="lbl">KEMARIN</div><div class="bignum">4,1</div></div>
    <div class="card-paper"><div class="lbl">HARI INI</div><div class="bignum" style="color:#E23B3B">6,5</div></div>
  </div>
  <svg viewBox="0 0 940 260" style="width:940px;margin-top:10px" filter="url(#wobble)">
    <path class="ink-blue draw" id="d0-arrow" pathLength="1" d="M180 60 C 340 10, 600 10, 760 60 M 720 30 L 762 62 L 716 92"/>
    <text x="470" y="200" text-anchor="middle" font-size="120" fill="#1a1a1a" font-family="Caveat">kok bisa?!</text>
  </svg>
</div>

<!-- SCENE 1 : konsep -->
<div class="scene" id="s1">
  <h1 class="hand">Namanya<br><span class="hl blue">delta check</span></h1>
  <p class="sub">bandingkan hasil baru vs kunjungan sebelumnya</p>
  <svg viewBox="0 0 940 560" style="width:940px;margin-top:20px" filter="url(#wobble)">
    <g class="ink" stroke-width="6">
      <circle class="draw" id="d1-h" pathLength="1" cx="470" cy="90" r="52"/>
      <path class="draw" id="d1-b" pathLength="1" d="M470 142 L470 330 M470 190 L350 260 M470 190 L590 260 M470 330 L380 480 M470 330 L560 480"/>
      <rect class="draw" id="d1-p1" pathLength="1" x="120" y="380" width="220" height="150" rx="10"/>
      <rect class="draw" id="d1-p2" pathLength="1" x="600" y="380" width="220" height="150" rx="10"/>
      <path class="draw ink-blue" id="d1-mag" pathLength="1" d="M230 430 m-55 0 a55 55 0 1 0 110 0 a55 55 0 1 0 -110 0 M270 470 L330 530"/>
    </g>
    <text x="230" y="470" text-anchor="middle" font-size="52" font-family="Caveat" fill="#1a1a1a">lama</text>
    <text x="710" y="470" text-anchor="middle" font-size="52" font-family="Caveat" fill="#1a1a1a">baru</text>
  </svg>
</div>

<!-- SCENE 2 : contoh angka -->
<div class="scene" id="s2">
  <h1 class="hand"><span class="blue">Kalium</span> 4,1 &rarr; 6,5</h1>
  <p class="sub">dalam seminggu, QC lolos, tanpa flag error</p>
  <div style="text-align:center;margin-top:40px">
    <div style="position:relative;display:inline-block">
      <div class="bignum" id="ncount" style="font-size:220px">4,1</div>
      <svg viewBox="0 0 560 340" style="position:absolute;left:-70px;top:-50px;width:560px;pointer-events:none" filter="url(#wobble)">
        <ellipse class="ink-red draw" id="d2-circ" pathLength="1" cx="280" cy="170" rx="250" ry="140"/>
      </svg>
    </div>
    <div class="hand" id="d2-stamp" style="font-size:96px;color:#E23B3B;transform:rotate(-8deg);opacity:0">EKSTREM!</div>
  </div>
</div>

<!-- SCENE 3 : aturan -->
<div class="scene" id="s3">
  <h1 class="hand">Aturannya <span class="hl">simpel</span></h1>
  <div style="margin-top:50px" filter="url(#wobble)">
    <div class="check"><svg width="90" height="90" viewBox="0 0 90 90"><rect class="ink-blue draw" id="d3-b1" pathLength="1" x="8" y="8" width="74" height="74" rx="14"/><path class="ink-red draw" id="d3-c1" pathLength="1" d="M22 46 L40 64 L70 28"/></svg><span>Tahan dulu</span></div>
    <div class="check"><svg width="90" height="90" viewBox="0 0 90 90"><rect class="ink-blue draw" id="d3-b2" pathLength="1" x="8" y="8" width="74" height="74" rx="14"/><path class="ink-red draw" id="d3-c2" pathLength="1" d="M22 46 L40 64 L70 28"/></svg><span>Validasi ulang</span></div>
  </div>
  <p class="sub" style="margin-top:30px">lewat batas delta &rarr; jangan auto-rilis</p>
</div>

<!-- SCENE 4 : closing -->
<div class="scene" id="s4">
  <div style="text-align:center">
    <svg viewBox="0 0 700 220" style="width:700px;margin:0 auto;display:block" filter="url(#wobble)">
      <rect class="ink-blue draw" id="d4-pill" pathLength="1" x="60" y="30" width="580" height="150" rx="75"/>
      <text x="350" y="140" text-anchor="middle" font-size="90" font-family="Caveat" fill="#1B5FD9">FastLIS</text>
    </svg>
    <h1 class="hand" style="font-size:80px;margin-top:30px">edukasi lab<br>setiap hari</h1>
    <div style="margin-top:40px"><span class="pill">Follow!</span></div>
  </div>
</div>

<div id="karaoke">{"".join(karaoke_divs)}</div>
</div>
<script src="../assets/gsap.min.js"></script>
<script>
var tl = gsap.timeline();
function setWord(i) {{
  document.querySelectorAll('.kw.on').forEach(e=>e.classList.remove('on'));
  var el = document.getElementById('w'+i); if(el) el.classList.add('on');
}}
function showPhrase(bi) {{
  document.querySelectorAll('.phrase').forEach(e=>e.style.display='none');
  var el = document.getElementById('p'+bi); if(el) el.style.display='block';
}}
function showScene(si) {{
  document.querySelectorAll('.scene').forEach(e=>e.classList.remove('on'));
  var el = document.getElementById('s'+si); if(el) el.classList.add('on');
  drawIn(si);
}}
function clearWords() {{
  document.querySelectorAll('.kw.on').forEach(e=>e.classList.remove('on'));
}}
function drawIn(si) {{
  var map = {{0:['d0-arrow'],1:['d1-h','d1-b','d1-p1','d1-p2','d1-mag'],2:['d2-circ'],3:['d3-b1','d3-c1','d3-b2','d3-c2'],4:['d4-pill']}};
  (map[si]||[]).forEach(function(id, k) {{
    var el = document.getElementById(id); if(!el) return;
    gsap.fromTo(el, {{strokeDashoffset:1}}, {{strokeDashoffset:0, duration:0.9, delay:k*0.35, ease:'power1.inOut'}});
  }});
  if (si===2) {{
    var o = {{v:4.1}};
    gsap.to(o, {{v:6.5, duration:1.6, ease:'power1.inOut',
      onUpdate:function(){{ document.getElementById('ncount').textContent = o.v.toFixed(1).replace('.', ','); }} }});
    gsap.to('#d2-stamp', {{opacity:1, duration:0.4, delay:1.8}});
  }}
}}
{calls_js}
</script>
</body></html>
"""
open(os.path.join(V2, "whiteboard.html"), "w").write(html)
print(f"whiteboard.html ditulis ({total}s)")
