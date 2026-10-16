#!/usr/bin/env python3
"""Whiteboard reels builder — TEMPLATE BARU FastLIS (menggantikan cinematic v2).
Gaya: kertas putih, tulisan tangan Caveat, garis digambar progresif (wobble),
aksen biru FastLIS, karaoke stabilo kuning, konten center vertikal.

Pakai: python3 scripts/build_reels_whiteboard.py  (beats di BEATS bawah)
Output: reels/v2/whiteboard.html + vo_whiteboard.mp3 + timings_whiteboard.json
Render: render_reels.py --html v2/whiteboard.html --out v2/whiteboard_raw.mp4 --duration <total>
Mux VO saja: ffmpeg -i raw -i vo_whiteboard.mp3 -c:v copy -c:a aac -shortest -movflags +faststart out.mp4
"""
import json, os, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(BASE, "reels", "v2")
sys.path.insert(0, os.path.join(BASE, "scripts"))
from build_reels_v2 import real_word_timings, audio_duration, esc, TTS, VOICE

# ---------------------------------------------------------------- beats
# scene: dict dengan type + param. types: title, flow, stage, stamp, checklist, closing
BEATS = [
    {"narr": "Hasil lab sudah keluar dari alat, tapi kok belum boleh dikasih ke dokter? Tenang, bukan error. Memang ada alurnya. Bayangkan pasien menunggu dan dokter menelepon, tapi sistem belum kasih lampu hijau.",
     "scene": {"type": "title", "ul_trigger": "dokter",
               "title": 'Kok belum boleh<br><span class="hl">dikasih ke dokter?</span>',
               "sub": "bukan error, memang ada alurnya"}},
    {"narr": "Di dalam LIS, setiap hasil harus melewati tiga tahap: pending, completed, lalu authorized. Tiga pintu berurutan, nggak bisa loncat.",
     "scene": {"type": "flow", "title": 'Tiga <span class="blue">tahap</span> wajib',
               "steps": ["PENDING", "COMPLETED", "AUTHORIZED"]}},
    {"narr": "Tahap satu, pending. Artinya hasil baru saja masuk dari alat atau input manual, dan belum dicek oleh siapa pun. Statusnya masih mentah, bisa saja salah karena sampel bermasalah atau alat error.",
     "scene": {"type": "stage", "word": "PENDING", "color": "#1a1a1a", "box_trigger": "pending",
               "descs": [["hasil baru masuk", "masuk"], ["belum dicek siapa pun", "dicek"]]}},
    {"narr": "Tahap dua, completed. Analis sudah memeriksa dan memverifikasi hasilnya, memastikan cocok dengan kondisi sampel dan riwayat pasien. Tapi ingat, ini belum final.",
     "scene": {"type": "stage", "word": "COMPLETED", "color": "#1a1a1a", "box_trigger": "completed",
               "descs": [["sudah diverifikasi analis", "memverifikasi"], ["tapi belum final", "final"]]}},
    {"narr": "Tahap tiga, authorized. Dokter penanggung jawab, biasanya dokter patologi klinik, sudah menyetujui hasilnya. Hanya di tahap inilah hasil boleh dirilis dan dikirim ke pasien.",
     "scene": {"type": "stage", "word": "AUTHORIZED", "color": "#1B5FD9", "box_trigger": "authorized",
               "descs": [["disetujui dokter PJ", "menyetujui"], ["baru boleh dirilis", "dirilis"]]}},
    {"narr": "Contoh jejak audit asli: tercatat Result flag updated to L by SYSTEM, lengkap dengan jam dan nilai inputnya. Kalau ada kesalahan, ketahuan siapa dan kapan.",
     "scene": {"type": "checklist", "title": '<span class="blue">jejak audit</span> nyata',
               "items": [["flag updated to L", "flag"], ["tercatat jamnya", "jam"], ["ketahuan siapa", "ketahuan"]]}},
    {"narr": "Kenapa harus seribet ini? Karena satu angka yang salah bisa mengubah diagnosis dan terapi pasien. Ingat kasus kalium 6,5 kemarin? Otorisasi itu rem daruratnya lab.",
     "scene": {"type": "stamp", "top": "1 angka salah", "circ_trigger": "salah",
               "stamp": "BAHAYA!", "stamp_trigger": "darurat", "sub": "bisa ubah diagnosis pasien"}},
    {"narr": "Bonusnya, setiap perpindahan tahap tercatat otomatis di jejak audit: siapa yang verifikasi, jam berapa, dan apa yang diubah. Transparan.",
     "scene": {"type": "checklist", "title": 'tercatat <span class="blue">otomatis</span>',
               "items": [["siapa yang verifikasi", "siapa"], ["jam berapa", "jam"], ["apa yang diubah", "diubah"]]}},
    {"narr": "Tips praktis: jangan pernah rilis hasil yang masih pending atau completed, walau dokternya sudah menelepon minta. Tunggu sampai authorized.",
     "scene": {"type": "title", "ul_trigger": "authorized",
               "title": 'Jangan rilis<br><span class="hl">sebelum <span class="blue">authorized</span></span>',
               "sub": "walau dokternya sudah menelepon"}},
    {"narr": "Jadi ingat urutannya: pending, completed, authorized. Follow FastLIS untuk edukasi lab setiap hari.",
     "scene": {"type": "closing"}},
]


WOBBLE = ('<svg width="0" height="0"><defs><filter id="wobble">'
          '<feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="2" result="n"/>'
          '<feDisplacementMap in="SourceGraphic" in2="n" scale="7"/>'
          '</filter></defs></svg>')

_draw_ids = []  # per scene: list of {id, trigger, kind, offset}


def _new_scene():
    _draw_ids.append([])


def _reg(id, trigger=None, kind="draw", offset=0):
    _draw_ids[-1].append({"id": id, "trigger": trigger, "kind": kind,
                          "offset": offset})


def scene_title(s, si):
    _new_scene()
    uid = f"s{si}-ul"
    _reg(uid, s.get("ul_trigger"), "draw")
    return (f'<div class="wrap"><h1 class="hand">{s["title"]}</h1>'
            f'<svg viewBox="0 0 600 40" style="width:600px;margin:6px auto 0;display:block" filter="url(#wobble)">'
            f'<path class="ink-blue draw" id="{uid}" pathLength="1" d="M20 22 C 200 12, 400 32, 580 20"/></svg>'
            f'<p class="sub">{esc(s["sub"])}</p></div>')


def scene_flow(s, si):
    _new_scene()
    steps = s["steps"]
    boxes = []
    xs = [20, 340, 660]
    for i, (st, x) in enumerate(zip(steps, xs)):
        trig = st.lower()
        bid = f"s{si}-fl-b{i}"
        _reg(bid, trig, "draw")
        boxes.append(
            f'<rect class="ink draw" id="{bid}" pathLength="1" x="{x}" y="60" width="260" height="150" rx="18"/>'
            f'<text x="{x+130}" y="150" text-anchor="middle" font-size="46" font-family="Caveat" fill="#1B5FD9">{st}</text>')
        if i < 2:
            aid = f"s{si}-fl-a{i}"
            _reg(aid, trig, "draw", offset=0.6)
            x1 = x + 260
            boxes.append(
                f'<path class="ink-blue draw" id="{aid}" pathLength="1" d="M{x1+8} 135 L{x1+52} 135 M{x1+32} 115 L{x1+54} 137 L{x1+32} 159"/>')
    inner = "\n".join(boxes)
    return (f'<div class="wrap"><h1 class="hand">{s["title"]}</h1>'
            f'<svg viewBox="0 0 940 270" style="width:940px;margin-top:30px" filter="url(#wobble)">{inner}</svg></div>')


def scene_stage(s, si):
    _new_scene()
    bid = f"s{si}-box"
    _reg(bid, s["box_trigger"], "draw")
    descs = ""
    for j, (d, trig) in enumerate(s["descs"]):
        did = f"s{si}-d{j}"
        _reg(did, trig, "reveal")
        descs += (f'<div class="checkline rv" id="{did}"><span class="dot"></span>'
                  f'<span>{esc(d)}</span></div>')
    return (f'<div class="wrap"><div class="stagecard"><svg viewBox="0 0 760 210" style="width:760px;display:block" filter="url(#wobble)">'
            f'<rect class="ink draw" id="{bid}" pathLength="1" x="10" y="10" width="740" height="190" rx="24"/>'
            f'<text x="380" y="140" text-anchor="middle" font-size="110" font-family="Caveat" fill="{s["color"]}">{s["word"]}</text>'
            f'</svg></div><div class="desclist">{descs}</div></div>')


def scene_stamp(s, si):
    _new_scene()
    cid, tid = f"s{si}-sp-circ", f"s{si}-sp-txt"
    _reg(cid, s["circ_trigger"], "draw")
    _reg(tid, s["stamp_trigger"], "reveal")
    return (f'<div class="wrap"><h1 class="hand">{esc(s["top"])}</h1>'
            f'<p class="sub">{esc(s["sub"])}</p>'
            f'<div style="position:relative;display:inline-block;margin-top:36px">'
            f'<svg viewBox="0 0 560 300" style="width:560px;display:block" filter="url(#wobble)">'
            f'<ellipse class="ink-red draw" id="s{si}-sp-circ" pathLength="1" cx="280" cy="150" rx="250" ry="125"/>'
            f'<text x="280" y="185" text-anchor="middle" font-size="100" font-family="Caveat" fill="#E23B3B" transform="rotate(-6 280 150)" opacity="0" id="{tid}">{s["stamp"]}</text>'
            f'</svg></div></div>')


def scene_checklist(s, si):
    _new_scene()
    rows = []
    for i, (it, trig) in enumerate(s["items"]):
        b, c, t = f"s{si}-ck-b{i}", f"s{si}-ck-c{i}", f"s{si}-ck-t{i}"
        _reg(b, trig, "draw")
        _reg(t, trig, "reveal", offset=0.15)
        _reg(c, trig, "draw", offset=0.45)
        rows.append(
            f'<div class="check"><svg width="90" height="90" viewBox="0 0 90 90" filter="url(#wobble)">'
            f'<rect class="ink-blue draw" id="{b}" pathLength="1" x="8" y="8" width="74" height="74" rx="14"/>'
            f'<path class="ink-red draw" id="{c}" pathLength="1" d="M22 46 L40 64 L70 28"/></svg>'
            f'<span id="{t}" class="rv">{esc(it)}</span></div>')
    return (f'<div class="wrap"><h1 class="hand">{s["title"]}</h1>'
            f'<div style="margin-top:30px">{"".join(rows)}</div></div>')


def scene_closing(_s=None, _si=None):
    _new_scene()
    _reg(f"s{_si}-cl-pill", "fastlis", "draw")
    return (f'<div class="wrap" style="text-align:center">'
            f'<svg viewBox="0 0 700 220" style="width:700px;margin:0 auto;display:block" filter="url(#wobble)">'
            f'<rect class="ink-blue draw" id="s{_si}-cl-pill" pathLength="1" x="60" y="30" width="580" height="150" rx="75"/>'
            f'<text x="350" y="140" text-anchor="middle" font-size="90" font-family="Caveat" fill="#1B5FD9">FastLIS</text>'
            f'</svg><h1 class="hand" style="font-size:80px;margin-top:30px">edukasi lab<br>setiap hari</h1>'
            f'<div style="margin-top:40px"><span class="pill">Follow!</span></div></div>')


BUILDERS = {"title": scene_title, "flow": scene_flow, "stage": scene_stage,
            "stamp": scene_stamp, "checklist": scene_checklist, "closing": scene_closing}

CSS = """
@font-face { font-family:'Caveat'; src:url('../assets/fonts/caveat-700.woff2') format('woff2'); font-weight:700; }
@font-face { font-family:'Poppins'; src:url('../assets/fonts/poppins-6.woff2') format('woff2'); font-weight:600; }
* { margin:0; padding:0; box-sizing:border-box; }
#root { width:1080px; height:1920px; position:relative; overflow:hidden;
  background:#FBF9F4; font-family:'Caveat',cursive; color:#1a1a1a; }
#root::before { content:''; position:absolute; inset:0;
  background-image:radial-gradient(#00000008 1px, transparent 1px);
  background-size:28px 28px; }
.scene { position:absolute; inset:0; display:none; padding:40px 70px 300px 70px; }
.scene.on { display:flex; flex-direction:column; }
.scene.on > *:first-child { margin-top:auto; }
.scene.on > *:last-child { margin-bottom:auto; }
.ink { stroke:#1a1a1a; stroke-width:7; fill:none; stroke-linecap:round; stroke-linejoin:round; }
.ink-red { stroke:#E23B3B; stroke-width:9; fill:none; stroke-linecap:round; }
.ink-blue { stroke:#1B5FD9; stroke-width:7; fill:none; stroke-linecap:round; }
.draw { stroke-dasharray:1; stroke-dashoffset:1; }
h1.hand { font-size:104px; line-height:1.08; text-align:center; }
h1.hand .hl { background:linear-gradient(transparent 8%, #FFE45E 8%, #FFE45E 92%, transparent 92%); padding:0 14px; }
h1.hand .blue, .blue { color:#1B5FD9; }
.sub { font-family:'Poppins',sans-serif; font-size:34px; color:#555; text-align:center; margin-top:18px; }
.wrap { width:100%; }
.stagecard { display:flex; justify-content:center; }
.desclist { margin-top:34px; }
.checkline { display:flex; align-items:center; justify-content:center; gap:18px; margin:16px 0;
  font-family:'Poppins',sans-serif; font-size:36px; }
.checkline .dot { width:16px; height:16px; border-radius:50%; background:#1B5FD9; flex:none; }
.check { display:flex; align-items:center; gap:26px; margin:26px 60px; font-size:60px; }
.pill { display:inline-block; border:5px solid #1a1a1a; border-radius:999px;
  padding:18px 54px; font-size:56px; background:#fff; box-shadow:5px 5px 0 #1a1a1a22; }
#karaoke { position:absolute; left:60px; right:60px; bottom:90px; min-height:190px;
  display:flex; align-items:center; justify-content:center; text-align:center; }
.phrase { font-family:'Poppins',sans-serif; font-weight:600; font-size:42px; line-height:1.5; color:#1a1a1a; }
.kw { padding:2px 8px; border-radius:8px; transition:background .12s; }
.kw.on { background:#FFE45E; }
.rv { opacity:0; }
#brand { position:absolute; top:56px; left:70px; font-family:'Poppins',sans-serif;
  font-weight:800; font-size:34px; letter-spacing:2px; }
#brand b { color:#1B5FD9; }
"""

JS = """
var tl = gsap.timeline();
function setWord(i) {
  document.querySelectorAll('.kw.on').forEach(e=>e.classList.remove('on'));
  var el = document.getElementById('w'+i); if(el) el.classList.add('on');
}
function showPhrase(bi) {
  document.querySelectorAll('.phrase').forEach(e=>e.style.display='none');
  var el = document.getElementById('p'+bi); if(el) el.style.display='block';
}

function clearWords() {
  document.querySelectorAll('.kw.on').forEach(e=>e.classList.remove('on'));
}
var BEAT_DURS = __BEATDURS__;
function drawEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {strokeDashoffset:1}, {strokeDashoffset:0, duration:0.9, ease:'power1.inOut'});
}
function revealEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {opacity:0, y:24}, {opacity:1, y:0, duration:0.6, ease:'power2.out'});
}
function drift(si) {
  var el = document.querySelector('#s'+si+' .wrap'); if(!el) return;
  gsap.fromTo(el, {scale:1}, {scale:1.05, duration:BEAT_DURS[si]||8, ease:'none', transformOrigin:'50% 50%'});
}
function showScene(si) {
  document.querySelectorAll('.scene').forEach(e=>e.classList.remove('on'));
  var el = document.getElementById('s'+si); if(el) el.classList.add('on');
  drift(si);
}
__CALLS__
"""


def main():
    # ---- TTS ----
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

    # ---- timings (whisper) ----
    words, bounds = [], []
    try:
        allw = [w for b in BEATS for w in b["narr"].split(" ")]
        rt = real_word_timings(vo_path, allw)
        t = 0.0
        for b in BEATS:
            ws = b["narr"].split(" ")
            t0 = t
            for w in ws:
                words.append({"w": w, "t0": round(rt[len(words)], 3)})
            t1 = rt[len(words) - 1] + 0.45
            bounds.append((round(t0, 3), round(t1, 3)))
            t = t1 + 0.15
        print(f"timing karaoke: REAL (whisper, {len(words)} kata)")
    except Exception as e:
        print(f"whisper gagal ({e}), pakai estimasi proporsional")
        t = 0.0
        tot_chars = max(1, len(narr_text.replace("\n", " ")))
        for b in BEATS:
            ws = b["narr"].split(" ")
            bd = dur * len(" ".join(ws)) / tot_chars
            for j, w in enumerate(ws):
                words.append({"w": w, "t0": round(t + bd * j / len(ws), 3)})
            bounds.append((round(t, 3), round(t + bd, 3)))
            t += bd + 0.15
    json.dump({"words": words, "bounds": bounds, "total": total},
              open(os.path.join(V2, "timings_whiteboard.json"), "w"), indent=1)

    # ---- scenes ----
    global _draw_ids
    _draw_ids = []
    scene_divs = []
    for si, b in enumerate(BEATS):
        fn = BUILDERS[b["scene"]["type"]]
        scene_divs.append(f'<div class="scene" id="s{si}">{fn(b["scene"], si)}</div>')

    # ---- karaoke ----
    wi = 0
    karaoke_divs = []
    for bi, b in enumerate(BEATS):
        spans = [f'<span class="kw" id="w{wi + j}">{esc(w)}</span>'
                 for j, w in enumerate(b["narr"].split(" "))]
        wi += len(spans)
        karaoke_divs.append(
            f'<div class="phrase" id="p{bi}" style="display:none">{" ".join(spans)}</div>')

    calls = [f'tl.call(setWord, [{i}], {wd["t0"]});' for i, wd in enumerate(words)]
    for bi, (a, bb) in enumerate(bounds):
        calls.append(f'tl.call(showPhrase, [{bi}], {a});')
        calls.append(f'tl.call(showScene, [{bi}], {a});')
        wmap = {}
        for wd in words:
            if a - 0.01 <= wd["t0"] <= bb + 0.01:
                key = wd["w"].lower().strip(".,!?;:\"'")
                wmap.setdefault(key, wd["t0"])
        regs = _draw_ids[bi]
        n = len(regs)
        for k, r in enumerate(regs):
            t = wmap.get((r["trigger"] or "").lower()) if r["trigger"] else None
            if t is None:
                t = a + (bb - a) * (0.12 + 0.76 * (k + 1) / (n + 1))
            t = round(t + r["offset"], 3)
            fn = "drawEl" if r["kind"] == "draw" else "revealEl"
            calls.append(f"tl.call({fn}, ['{r['id']}'], {t});")
    calls.append(f'tl.call(clearWords, [], {total - 0.05});')

    beat_durs = [round(bb - a, 2) for a, bb in bounds]
    js = JS.replace("__BEATDURS__", json.dumps(beat_durs)).replace(
        "__CALLS__", "\n".join(calls))

    html = (f'<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>'
            f'<div id="root" data-composition-id="whiteboard" data-start="0" '
            f'data-duration="{total}" data-width="1080" data-height="1920">'
            f'<div id="brand">FAST<b>LIS</b></div>{WOBBLE}'
            f'{"".join(scene_divs)}'
            f'<div id="karaoke">{"".join(karaoke_divs)}</div></div>'
            f'<script src="../assets/gsap.min.js"></script><script>{js}</script>'
            f'</body></html>')
    open(os.path.join(V2, "whiteboard.html"), "w").write(html)
    print(f"whiteboard.html ditulis ({total}s), {len(BEATS)} scene")


if __name__ == "__main__":
    main()
