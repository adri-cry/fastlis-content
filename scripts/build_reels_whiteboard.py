#!/usr/bin/env python3
"""Whiteboard reels builder — TEMPLATE BARU FastLIS (menggantikan cinematic v2).
Gaya: kertas putih, tulisan tangan Caveat, garis digambar progresif (wobble),
aksen biru FastLIS, karaoke stabilo kuning, konten center vertikal,
kamera variatif per tipe scene (zin/zout/pan) + punch + reveal pop.

Pakai:
  python3 scripts/build_reels_whiteboard.py                 # BEATS hardcoded -> whiteboard.html
  python3 scripts/build_reels_whiteboard.py --beats f.json [--prefix p]
      # beats dari JSON (skema sama kayak BEATS) -> reels/v2/<p>.html
  python3 scripts/build_reels_whiteboard.py --daily        # susun beats generik
      # dari content/hari-ini.json key "reels" (s1..s6) -> reels/v2/daily.html
      # (nama file SAMA kayak builder v2 supaya langkah cron 4-8 tidak berubah)
Render: render_reels.py --html v2/<prefix>.html --out v2/<prefix>_raw.mp4 --duration <total>
Mux VO saja: ffmpeg -i raw -i vo_<prefix>.mp3 -c:v copy -c:a aac -shortest -movflags +faststart out.mp4
"""
import json, os, re, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(BASE, "reels", "v2")
sys.path.insert(0, os.path.join(BASE, "scripts"))
from build_reels_v2 import real_word_timings, audio_duration, esc, TTS, VOICE, strip_html, join_spoken

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
    cid, tid, pid = f"s{si}-sp-circ", f"s{si}-sp-txt", f"s{si}-punch"
    _reg(cid, s["circ_trigger"], "draw")
    _reg(tid, s["stamp_trigger"], "reveal")
    _reg(pid, s["stamp_trigger"], "punch", offset=0.1)
    return (f'<div class="wrap"><h1 class="hand">{esc(s["top"])}</h1>'
            f'<p class="sub">{esc(s["sub"])}</p>'
            f'<div id="{pid}" style="position:relative;display:inline-block;margin-top:36px">'
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


# ------------------------------------------------- composer generik harian
# Petakan s1..s6 hari-ini.json (struktur yang sama dipakai builder v2)
# ke scene whiteboard. Trigger animasi dipilih dari kata isi narasi;
# kalau kata tidak ketemu di timing whisper, builder pakai fallback
# proporsional (tidak error, animasi tetap jalan).
_STOP = {"yang", "dan", "atau", "dengan", "untuk", "dari", "ini", "itu",
        "adalah", "bisa", "akan", "jadi", "sudah", "belum", "tidak", "nggak",
        "jangan", "kamu", "kita", "mereka", "saya", "apa", "bagaimana",
        "kenapa", "kapan", "berapa", "agar", "supaya", "saat", "ketika",
        "dalam", "pada", "oleh", "antara", "setiap", "semua", "ada", "pun",
        "saja", "juga", "sangat", "lebih", "kurang", "bukan", "kalau"}


def _pick_trigger(narr, fallback=""):
    for w in narr.split(" "):
        k = w.lower().strip(".,!?;:\"'()")
        if len(k) > 3 and k not in _STOP and k.isalpha():
            return k
    return fallback


def compose_daily_beats(path=None):
    """Susun beats whiteboard generik dari content/hari-ini.json key 'reels'."""
    jp = path or os.path.join(BASE, "content", "hari-ini.json")
    r = json.load(open(jp))["reels"]
    beats = []

    # s1: hook -> title (underline digambar pas kata kunci disebut)
    d1 = r.get("s1", {})
    n1 = join_spoken(strip_html(d1.get("h1", "")), strip_html(d1.get("sub", "")))
    beats.append({
        "narr": n1,
        "scene": {"type": "title",
                  "title": d1.get("h1", ""),
                  "sub": strip_html(d1.get("sub", "")),
                  "ul_trigger": _pick_trigger(n1)}})

    # s2: konteks/kasus -> stage (kotak besar + 2 baris penjelasan)
    d2 = r.get("s2", {})
    n2 = join_spoken(strip_html(d2.get("h1", "")), strip_html(d2.get("sub", "")))
    kicker = strip_html(d2.get("kicker", "info")).split(" ")
    word2 = (kicker[0] if kicker else "info").upper()[:10] or "INFO"
    h1b, sub2 = strip_html(d2.get("h1", "")), strip_html(d2.get("sub", ""))
    beats.append({
        "narr": n2,
        "scene": {"type": "stage", "word": word2, "color": "#1B5FD9",
                  "box_trigger": _pick_trigger(n2, word2.lower()),
                  "descs": [[h1b, _pick_trigger(h1b)],
                            [sub2, _pick_trigger(sub2)]]}})

    # s3-s5: 3 poin bernomor -> stage (angka besar di kotak)
    for k in ("s3", "s4", "s5"):
        dd = r.get(k, {})
        title = strip_html(dd.get("title", ""))
        m = re.match(r"\s*(\d+)", title)
        word = m.group(1) if m else "•"
        desc, sub = strip_html(dd.get("desc", "")), strip_html(dd.get("sub", ""))
        n = join_spoken(title, sub, desc)
        beats.append({
            "narr": n,
            "scene": {"type": "stage", "word": word, "color": "#1a1a1a",
                      "box_trigger": _pick_trigger(n, word),
                      "descs": [[desc, _pick_trigger(desc)],
                                [sub, _pick_trigger(sub)]]}})

    # s6: closing -> checklist dari pills (takeaway hari ini)
    d6 = r.get("s6", {})
    n6 = join_spoken(strip_html(d6.get("h1", "")), strip_html(d6.get("sub", "")))
    pills = [p for p in (d6.get("pills") or []) if strip_html(p)]
    if pills:
        items = [[strip_html(p), _pick_trigger(strip_html(p), "fastlis")]
                 for p in pills]
        beats.append({
            "narr": n6,
            "scene": {"type": "checklist", "title": d6.get("h1", ""), "items": items}})
    else:
        beats.append({
            "narr": n6,
            "scene": {"type": "title", "title": d6.get("h1", ""),
                      "sub": strip_html(d6.get("sub", "")),
                      "ul_trigger": _pick_trigger(n6)}})

    # variasi kamera: jangan dua beat berurutan pakai gerakan yang sama
    # (beat "cam" opsional; kalau tidak diisi, build_from_beats pakai default per tipe)
    _flip = {"zin": "zout", "zout": "zin", "panr": "panl", "panl": "panr"}
    _defcam = {"title": "zin", "flow": "panr", "stage": "zin",
               "stamp": "zin", "checklist": "zout", "closing": "zout"}
    last = None
    for b in beats:
        c = _defcam[b["scene"]["type"]]
        if c == last:
            c = _flip.get(c, c)
        b["cam"] = c
        last = c
    return beats

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
var BEAT_CAM = __BEATCAM__;
function drawEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {strokeDashoffset:1}, {strokeDashoffset:0, duration:0.9, ease:'power1.inOut'});
}
function revealEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {opacity:0, y:26, scale:0.92}, {opacity:1, y:0, scale:1, duration:0.55, ease:'back.out(1.5)'});
}
function camera(si) {
  var el = document.querySelector('#s'+si+' .wrap'); if(!el) return;
  var dur = BEAT_DURS[si]||8, kind = BEAT_CAM[si]||'zin', o = {transformOrigin:'50% 50%', ease:'power1.inOut'};
  if (kind==='zin') gsap.fromTo(el, {scale:1}, {scale:1.08, duration:dur, ...o});
  else if (kind==='zout') gsap.fromTo(el, {scale:1.08}, {scale:1.0, duration:dur, ...o});
  else if (kind==='panr') gsap.fromTo(el, {x:-55, scale:1.04}, {x:55, scale:1.04, duration:dur, ...o});
  else if (kind==='panl') gsap.fromTo(el, {x:55, scale:1.04}, {x:-55, scale:1.04, duration:dur, ...o});
}
function punch(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.timeline()
    .to(el, {scale:1.16, duration:0.22, ease:'power3.out', transformOrigin:'50% 50%'})
    .to(el, {scale:1.0, duration:0.5, ease:'back.out(1.6)'});
}
function showScene(si) {
  document.querySelectorAll('.scene').forEach(e=>e.classList.remove('on'));
  var el = document.getElementById('s'+si); if(el) el.classList.add('on');
  camera(si);
}
__CALLS__
"""


def build_from_beats(beats, prefix="whiteboard"):
    """Bangun VO + timing karaoke + HTML whiteboard dari daftar beats generik.

    beats: list of {"narr": str, "scene": {"type": ..., ...}}
    Output: reels/v2/<prefix>.html, vo_<prefix>.mp3, timings_<prefix>.json
    """
    # ---- TTS ----
    narr_text = "\n".join(b["narr"] for b in beats)
    vo_path = os.path.join(V2, f"vo_{prefix}.mp3")
    open(os.path.join(V2, f"vo_{prefix}.txt"), "w").write(narr_text)
    cp = subprocess.run([TTS, "speak", "--language", "id", "--voice", VOICE,
                         "--output", vo_path, "--text-stdin"],
                        input=narr_text.encode(), capture_output=True)
    if cp.returncode != 0 or not os.path.exists(vo_path):
        print("TTS GAGAL:", cp.stderr.decode()[:500]); sys.exit(1)
    dur = audio_duration(vo_path)
    total = round(dur + 0.6, 2)
    print(f"VO jadi: {dur:.1f}s, total render {total}s")
    # ---- penjaga durasi: tangkap halusinasi TTS tanpa dengerin manual ----
    est = max(1, len(narr_text.replace("\n", " "))) / 850 * 60
    if abs(dur - est) / est > 0.30:
        print(f"PERINGATAN durasi VO: aktual {dur:.1f}s vs estimasi {est:.1f}s "
              f"(selisih >30%, mungkin halusinasi TTS — cek vo_{prefix}.mp3)")

    # ---- timings (whisper) ----
    words, bounds = [], []
    try:
        allw = [w for b in beats for w in b["narr"].split(" ")]
        rt = real_word_timings(vo_path, allw)
        if not rt or len(rt) < len(allw):
            raise ValueError("timing whisper tidak lengkap")
        t = 0.0
        for b in beats:
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
        words, bounds = [], []  # buang hasil parsial supaya tidak tercampur
        t = 0.0
        tot_chars = max(1, len(narr_text.replace("\n", " ")))
        for b in beats:
            ws = b["narr"].split(" ")
            bd = dur * len(" ".join(ws)) / tot_chars
            for j, w in enumerate(ws):
                words.append({"w": w, "t0": round(t + bd * j / len(ws), 3)})
            bounds.append((round(t, 3), round(t + bd, 3)))
            t += bd + 0.15
    json.dump({"words": words, "bounds": bounds, "total": total},
              open(os.path.join(V2, f"timings_{prefix}.json"), "w"), indent=1)

    # ---- scenes ----
    global _draw_ids
    _draw_ids = []
    scene_divs = []
    for si, b in enumerate(beats):
        fn = BUILDERS[b["scene"]["type"]]
        scene_divs.append(f'<div class="scene" id="s{si}">{fn(b["scene"], si)}</div>')

    # ---- karaoke ----
    wi = 0
    karaoke_divs = []
    for bi, b in enumerate(beats):
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
            fn = {"draw": "drawEl", "reveal": "revealEl", "punch": "punch"}[r["kind"]]
            calls.append(f"tl.call({fn}, ['{r['id']}'], {t});")
    calls.append(f'tl.call(clearWords, [], {total - 0.05});')

    beat_durs = [round(bb - a, 2) for a, bb in bounds]
    cam = {"title": "zin", "flow": "panr", "stage": "zin", "stamp": "zin",
           "checklist": "zout", "closing": "zout"}
    beat_cams = [b.get("cam") or cam[b["scene"]["type"]] for b in beats]
    js = JS.replace("__BEATDURS__", json.dumps(beat_durs)).replace(
        "__BEATCAM__", json.dumps(beat_cams)).replace(
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
    open(os.path.join(V2, f"{prefix}.html"), "w").write(html)
    print(f"{prefix}.html ditulis ({total}s), {len(beats)} scene")


def main():
    beats, prefix = BEATS, "whiteboard"
    args = sys.argv[1:]
    daily = "--daily" in args
    if daily:
        beats = compose_daily_beats()
        prefix = "daily"
        print(f"mode daily: {len(beats)} beats dari content/hari-ini.json")
    elif "--beats" in args:
        i = args.index("--beats")
        beats = json.load(open(args[i + 1]))
        if "--prefix" in args:
            prefix = args[args.index("--prefix") + 1]
        print(f"mode beats-file: {len(beats)} beats, prefix={prefix}")
    build_from_beats(beats, prefix)
    if daily:
        # paritas dengan builder v2 supaya langkah cron 2 & 5 tidak berubah
        from build_reels_v2 import write_status, JINGLE_VARIANTS, today_wib
        doy = today_wib().timetuple().tm_yday
        print(f"VARIANT={JINGLE_VARIANTS[doy % 4]}")
        write_status("siap-render", 100, "daily.html siap dirender")


if __name__ == "__main__":
    main()
