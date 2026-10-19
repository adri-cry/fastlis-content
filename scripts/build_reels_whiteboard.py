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
import datetime
import json, os, re, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(BASE, "reels", "v2")
sys.path.insert(0, os.path.join(BASE, "scripts"))
ASSETS = os.path.join(BASE, "reels", "assets")
TTS = "/opt/hatch/bin/tts"
VOICE = "avocado_v2:MAI_01"
JINGLE_VARIANTS = ["original", "chill", "energetic", "minimal"]
WHISPER_PY = os.path.expanduser("~/workspace/venvs/whisper/bin/python")
WHISPER_TIMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper_times.py")


def today_wib():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))


def strip_html(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", s).strip()


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def join_spoken(*parts):
    """Gabung potongan copy jadi kalimat narasi tanpa tanda baca dobel."""
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out:
            prev = out[-1]
            if prev and prev[-1] not in ".?!…":
                out[-1] = prev + "."
        out.append(p)
    text = " ".join(out)
    if text and text[-1] not in ".?!…":
        text += "."
    return text


def audio_duration(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=noprint_wrappers=1", p],
                       capture_output=True, text=True)
    return float(r.stdout.strip().split("=")[1])


def _norm_w(s):
    return "".join(c for c in s.lower() if c.isalnum())


def real_word_timings(vo_path, narr_words):
    """Timestamp kata asli dari audio via whisper. Kembalikan list t0 per kata
    narasi, atau None kalau gagal (fallback ke estimasi proporsional)."""
    import difflib
    try:
        cp = subprocess.run(
            [WHISPER_PY, WHISPER_TIMES, vo_path],
            capture_output=True, text=True, timeout=600)
        wt = json.loads(cp.stdout)
        if not wt or isinstance(wt, dict):
            return None
        nw = [_norm_w(w) for w in narr_words]
        ww = [_norm_w(x["w"]) for x in wt]
        sm = difflib.SequenceMatcher(None, nw, ww, autojunk=False)
        t0s = [None] * len(nw)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal" and i2 > i1:
                for k in range(i2 - i1):
                    t0s[i1 + k] = wt[j1 + k]["t0"]
            else:
                t_start = wt[j1]["t0"] if j1 < len(wt) else (wt[-1]["t1"] if wt else 0)
                t_end = wt[j2 - 1]["t1"] if j2 > j1 else t_start + 0.3 * max(1, i2 - i1)
                n = max(1, i2 - i1)
                for k in range(n):
                    t0s[i1 + k] = round(t_start + (t_end - t_start) * k / n, 3)
        last = 0.0
        for i in range(len(t0s)):
            if t0s[i] is None:
                t0s[i] = last
            else:
                last = t0s[i]
        return t0s
    except Exception as e:
        print(f"whisper timing gagal ({e}), pakai estimasi proporsional")
        return None


def write_status(stage, progress=0, detail="", video=None):
    """Tulis reels/v2/render_status.json untuk dipantau dashboard."""
    st = {"stage": stage, "progress": round(progress, 1), "detail": detail,
          "updated_at": today_wib().strftime("%Y-%m-%dT%H:%M:%S+07:00"),
          "video": video}
    try:
        json.dump(st, open(os.path.join(V2, "render_status.json"), "w"))
    except Exception:
        pass


def _build_sfx_track(sched, total_dur, out_wav):
    """Campur SFX sesuai jadwal -> satu track wav (volume 25% sesuai spec)."""
    import wave
    import numpy as np
    sr = 44100
    n = int((total_dur + 1.0) * sr)
    mix = np.zeros(n, dtype=np.float32)
    cache = {}
    for ev in sched:
        name = ev["sfx"]
        if name not in cache:
            p = os.path.join(ASSETS, f"sfx-{name}.wav")
            if not os.path.exists(p):
                continue
            w = wave.open(p, "rb")
            s = w.readframes(w.getnframes())
            w.close()
            cache[name] = np.frombuffer(s, dtype=np.int16).astype(np.float32) / 32768.0
        if name not in cache:
            continue
        y = cache[name] * 0.25
        at = int(ev["t"] * sr)
        if 0 <= at < n:
            m = min(len(y), n - at)
            mix[at:at + m] += y[:m]
    mix = np.clip(mix, -1, 1)
    w = wave.open(out_wav, "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
    w.close()
    return out_wav


def mux(render_mp4, vo_mp3, out_mp4, variant):
    """Gabung render + VO + jingle varian + SFX -> mp4 faststart siap WhatsApp."""
    jingle = os.path.join(ASSETS, f"jingle-{variant}.wav")
    if not os.path.exists(jingle):
        jingle = os.path.join(ASSETS, "fastlis-jingle.wav")
    dur = audio_duration(vo_mp3)
    # SFX: dari sfx_<prefix>.json (prefix dari nama vo)
    _pre = os.path.basename(vo_mp3).replace("vo_", "").replace(".mp3", "")
    _sched_p = os.path.join(V2, f"sfx_{_pre}.json")
    _sfx_wav = os.path.join(V2, f"sfx_{_pre}.wav")
    _sched = json.load(open(_sched_p)) if os.path.exists(_sched_p) else []
    _build_sfx_track(_sched, dur, _sfx_wav)
    print(f"sfx: {len(_sched)} event -> {_sfx_wav}")
    fade_st = max(0, round(dur - 2.5, 1))
    fc = (f"[1:a]volume=1.0[vo];[2:a]atrim=0:{round(dur + 1)},volume=0.12,"
          f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_st}:d=2.5[bg];"
          f"[3:a]volume=1.0[fx];"
          f"[vo][bg][fx]amix=inputs=3:duration=longest:dropout_transition=0[a]")
    cp = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", render_mp4, "-i", vo_mp3,
         "-i", jingle, "-i", _sfx_wav,
         "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", out_mp4],
        capture_output=True, text=True)
    if cp.returncode != 0:
        print("MUX GAGAL:", cp.stderr[-500:])
        return 1
    print("mux ok:", out_mp4, f"(jingle: {os.path.basename(jingle)})")
    return 0

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
          '<feTurbulence id="boilTurb" type="fractalNoise" baseFrequency="0.015" numOctaves="2" seed="7" result="n"/>'
          '<feDisplacementMap in="SourceGraphic" in2="n" scale="7"/>'
          '</filter></defs></svg>')

_draw_ids = []  # per scene: list of {id, trigger, kind, offset}


def _new_scene():
    _draw_ids.append([])


def _reg(id, trigger=None, kind="draw", offset=0, **kw):
    d = {"id": id, "trigger": trigger, "kind": kind, "offset": offset}
    d.update(kw)
    _draw_ids[-1].append(d)



def _arc(cx, cy, r, frac=0.985):
    """Path busur hampir penuh, dijamin konsentris di (cx,cy) radius r."""
    import math as _m
    a0 = -_m.pi / 2
    a1 = a0 + frac * 2 * _m.pi
    return (f"M{cx + r * _m.cos(a0):.1f} {cy + r * _m.sin(a0):.1f} "
            f"A{r:.0f} {r:.0f} 0 1 1 {cx + r * _m.cos(a1):.1f} {cy + r * _m.sin(a1):.1f}")


def _key(w):
    return w.lower().strip(".,!?;:\"'()…")


MARKER = ('<g class="marker" opacity="0"><g transform="translate(0,-14) rotate(30)">'
          '<rect x="-13" y="-115" width="26" height="105" rx="9" fill="#1B5FD9"/>'
          '<rect x="-13" y="-115" width="26" height="30" rx="9" fill="#0d3a8a"/>'
          '<polygon points="-13,-10 13,-10 0,14" fill="#1a1a1a"/>'
          '<circle cx="0" cy="-142" r="24" fill="#f0b48a"/>'
          '<rect x="-26" y="-162" width="52" height="26" rx="12" fill="#f0b48a"/>'
          '</g></g>')


def _w3(html, si, pfx):
    """Bungkus tiap kata jadi span.w3; kembalikan (html, [(id, kata)])."""
    parts = re.split(r"(<br\s*/?>|<span[^>]*>|</span>)", html)
    out, ids, n = [], [], [0]
    for p in parts:
        if not p:
            continue
        if p.startswith("<span") and p != "</span>":
            out.append('<span class="blue">' if "blue" in p else "<span>")
            continue
        if p == "</span>":
            out.append("</span>")
            continue
        if p.startswith("<br"):
            out.append("<br>")
            continue
        for w in p.split(" "):
            if not w:
                continue
            wid = f"s{si}-{pfx}w{n[0]}"
            n[0] += 1
            ids.append((wid, w))
            out.append(f'<span class="w3" id="{wid}">{esc(w)}</span> ')
    return "".join(out), ids


def scene_title(s, si, narr=None):
    _new_scene()
    uid = f"s{si}-ul"
    _reg(uid, s.get("ul_trigger"), "draw")
    tid = f"s{si}-title"
    thtml, wids = _w3(s["title"], si, "t")
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
    _reg(tid, "^", "idle", offset=0.8)  # gerak halus sustain
    sid = f"s{si}-sub"
    _reg(sid, s.get("ul_trigger"), "pop", offset=0.3)
    return (f'<div class="wrap"><h1 class="hand" id="{tid}">{thtml}</h1>'
            f'<svg viewBox="0 0 600 40" style="width:600px;margin:6px auto 0;display:block" filter="url(#wobble)">'
            f'<path class="ink-blue draw" id="{uid}" pathLength="1" d="M20 22 C 200 12, 400 32, 580 20"/>{MARKER}</svg>'
            f'<p class="sub pop0" id="{sid}">{esc(s["sub"])}</p></div>')


def scene_flow(s, si, narr=None):
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


def scene_stage(s, si, narr=None):
    _new_scene()
    bid = f"s{si}-box"
    _reg(bid, s["box_trigger"], "draw")
    _reg(bid, s["box_trigger"], "emphasis", offset=0.65)  # punch saat kata kunci
    _reg(bid, s["box_trigger"], "idle", offset=1.1)       # gerak halus sustain
    fid = f"s{si}-flourish"
    _reg(fid, s["box_trigger"], "draw", offset=1.4, dur=0.7)  # ornamen digambar
    descs = ""
    for j, (d, trig) in enumerate(s["descs"]):
        did = f"s{si}-d{j}"
        _reg(did, trig, "reveal")
        descs += (f'<div class="checkline rv" id="{did}"><span class="dot"></span>'
                  f'<span>{esc(d)}</span></div>')
    return (f'<div class="wrap"><div class="stagecard"><svg viewBox="0 0 760 260" style="width:760px;display:block" filter="url(#wobble)">'
            f'<rect class="ink draw" id="{bid}" pathLength="1" x="10" y="10" width="740" height="190" rx="24"/>'
            f'<text x="380" y="140" text-anchor="middle" font-size="110" font-family="Caveat" fill="{s["color"]}">{s["word"]}</text>'
            f'<path class="ink-blue draw" id="{fid}" pathLength="1" d="M120 232 C 300 218, 480 244, 640 228"/>'
            f'{MARKER}</svg></div><div class="desclist">{descs}</div></div>')


def scene_stamp(s, si, narr=None):
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


def scene_checklist(s, si, narr=None):
    _new_scene()
    tid = f"s{si}-ck-title"
    rows = []
    for i, (it, trig) in enumerate(s["items"]):
        b, c, t = f"s{si}-ck-b{i}", f"s{si}-ck-c{i}", f"s{si}-ck-t{i}"
        _reg(b, trig, "draw")
        _reg(t, trig, "reveal", offset=0.15)
        _reg(c, trig, "draw", offset=0.45)
        _reg(c, trig, "emphasis", offset=0.75)  # punch saat centang jadi
        if i == 0:
            _reg(tid, trig, "punch", offset=0)  # judul punch bareng item pertama
        rows.append(
            f'<div class="check"><svg width="90" height="90" viewBox="0 0 90 90" filter="url(#wobble)">'
            f'<rect class="ink-blue draw" id="{b}" pathLength="1" x="8" y="8" width="74" height="74" rx="14"/>'
            f'<path class="ink-red draw" id="{c}" pathLength="1" d="M22 46 L40 64 L70 28"/></svg>'
            f'<span id="{t}" class="rv">{esc(it)}</span></div>')
    return (f'<div class="wrap"><h1 class="hand" id="{tid}">{s["title"]}</h1>'
            f'<div style="margin-top:30px">{"".join(rows)}</div></div>')


def scene_closing(_s=None, _si=None, narr=None):
    _new_scene()
    _reg(f"s{_si}-cl-pill", "fastlis", "draw")
    return (f'<div class="wrap" style="text-align:center">'
            f'<svg viewBox="0 0 700 220" style="width:700px;margin:0 auto;display:block" filter="url(#wobble)">'
            f'<rect class="ink-blue draw" id="s{_si}-cl-pill" pathLength="1" x="60" y="30" width="580" height="150" rx="75"/>'
            f'<text x="350" y="140" text-anchor="middle" font-size="90" font-family="Caveat" fill="#1B5FD9">FastLIS</text>'
            f'</svg><h1 class="hand" style="font-size:80px;margin-top:30px">edukasi lab<br>setiap hari</h1>'
            f'<div style="margin-top:40px"><span class="pill">Follow!</span></div></div>')



# ------------------------------------------------- scene TAT (spec Adri 2026-10-17)

def _ticks(cx, cy, r1, r2, n=12, cls="ink", sw=6):
    import math
    out = []
    for i in range(n):
        a = i / n * 2 * math.pi
        x1, y1 = cx + r1 * math.cos(a), cy + r1 * math.sin(a)
        x2, y2 = cx + r2 * math.cos(a), cy + r2 * math.sin(a)
        out.append(f'<line class="{cls}" x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke-width="{sw}"/>')
    return "".join(out)


def scene_title_sw(s, si, narr=None):
    _new_scene()
    P = f"s{si}"
    _reg(f"{P}-sw-circ", "^", "draw", offset=0)
    _reg(f"{P}-sw-arc", "^", "draw", offset=0.1, dur=0.5)
    _reg(f"{P}-sw-ticks", "^", "pop", offset=0.2)
    _reg(f"{P}-sw-hands", "^", "spin", offset=0, svgOrigin="200 180")
    _reg(f"{P}-sw-btn", "^", "pop", offset=0.25)
    thtml, wids = _w3(s["title"], si, "t")
    emph_id = None
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
        if _key(w) == "telat":
            emph_id = wid
    if emph_id:
        _reg(emph_id, "telat", "emphasis", offset=0.1)
    _reg(f"{P}-t-ul", "telat", "draw", offset=0.05, dur=0.5)
    _reg(f"{P}-t-sub", "3", "pop")
    ticks = _ticks(200, 180, 108, 124)
    return (f'<div class="wrap" style="text-align:center">'
            f'<svg viewBox="0 0 400 380" style="width:360px;margin:0 auto;display:block" filter="url(#wobble)">'
            f'<rect class="ink pop0" id="{P}-sw-btn" x="182" y="14" width="36" height="30" rx="9"/>'
            f'<line class="ink" x1="200" y1="44" x2="200" y2="58" stroke-width="8"/>'
            f'<circle class="ink draw" id="{P}-sw-circ" pathLength="1" cx="200" cy="180" r="130"/>'
            f'<path class="ink-red draw" id="{P}-sw-arc" pathLength="1" d="{_arc(200, 180, 140)}"/>'
            f'<g id="{P}-sw-ticks" class="pop0">{ticks}</g>'
            f'<g id="{P}-sw-hands"><line class="ink" x1="200" y1="180" x2="200" y2="92" stroke-width="9"/>'
            f'<line class="ink" x1="200" y1="180" x2="262" y2="180" stroke-width="9"/>'
            f'<circle cx="200" cy="180" r="12" fill="#1a1a1a"/></g>'
            f'{MARKER}</svg>'
            f'<h1 class="hand" style="margin-top:26px">{thtml}</h1>'
            f'<svg viewBox="0 0 640 44" style="width:560px;margin:6px auto 0;display:block" filter="url(#wobble)">'
            f'<path class="ink-red draw" id="{P}-t-ul" pathLength="1" d="M40 24 C 200 12, 420 34, 600 20"/>'
            f'{MARKER}</svg>'
            f'<p class="sub pop0" id="{P}-t-sub" style="font-size:40px">{esc(s["sub"])}</p></div>')


def scene_timeline(s, si, narr=None):
    _new_scene()
    P = f"s{si}"
    _reg(f"{P}-tl-box", "timer", "draw")
    _reg(f"{P}-tl-tube", "sampel", "draw")
    _reg(f"{P}-tl-tubein", "sampel", "pop", offset=0.35)
    _reg(f"{P}-tl-line", "sampel", "draw", offset=0.4, dur=1.2)
    _reg(f"{P}-tl-msw", "sampel", "slidex", offset=0.4, x=500, dur=1.2)
    _reg(f"{P}-tl-paper", "dirilis", "pop")
    _reg(f"{P}-tl-paper", "dirilis", "emphasis", offset=0.2)
    _reg(f"{P}-tl-lab1", "sampel", "pop", offset=0.5)
    _reg(f"{P}-tl-lab2", "dirilis", "pop", offset=0.3)
    bhtml, wids = _w3(" ".join(s["baris"]), si, "b")
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
    return (f'<div class="wrap" style="text-align:center">'
            f'<svg viewBox="0 0 760 210" style="width:640px;margin:0 auto;display:block" filter="url(#wobble)">'
            f'<rect class="ink draw" id="{P}-tl-box" pathLength="1" x="10" y="10" width="740" height="190" rx="24"/>'
            f'<text x="380" y="140" text-anchor="middle" font-size="104" font-family="Caveat" fill="{s["color"]}">DEFINISI</text>'
            f'{MARKER}</svg>'
            f'<svg viewBox="0 0 920 400" style="width:800px;margin:26px auto 0;display:block" filter="url(#wobble)">'
            f'<g><rect class="ink draw" id="{P}-tl-tube" pathLength="1" x="100" y="110" width="96" height="170" rx="22"/>'
            f'<rect id="{P}-tl-tubein" class="pop0" x="116" y="180" width="64" height="84" rx="12" fill="#1B5FD9" opacity="0.75"/></g>'
            f'<path class="ink draw" id="{P}-tl-line" pathLength="1" d="M210 195 L710 195"/>'
            f'<g id="{P}-tl-msw" transform="translate(210,195)"><circle class="ink" cx="0" cy="0" r="36" fill="#FBF9F4"/>'
            f'<line class="ink" x1="0" y1="0" x2="0" y2="-20" stroke-width="7"/>'
            f'<line class="ink" x1="0" y1="0" x2="14" y2="0" stroke-width="7"/></g>'
            f'<g id="{P}-tl-paper" class="pop0"><rect class="ink" x="690" y="105" width="130" height="180" rx="12" fill="#fff"/>'
            f'<line class="ink" x1="710" y1="150" x2="800" y2="150" stroke-width="6"/>'
            f'<line class="ink" x1="710" y1="185" x2="800" y2="185" stroke-width="6"/>'
            f'<line class="ink-blue" x1="710" y1="220" x2="780" y2="220" stroke-width="8"/></g>'
            f'<text id="{P}-tl-lab1" class="pop0" x="148" y="330" text-anchor="middle" font-size="30" font-family="Poppins" font-weight="600">SAMPEL DITERIMA</text>'
            f'<text id="{P}-tl-lab2" class="pop0" x="755" y="330" text-anchor="middle" font-size="30" font-family="Poppins" font-weight="600">HASIL DIRILIS</text>'
            f'{MARKER}</svg>'
            f'<p class="bar1" style="margin-top:18px">{bhtml}</p></div>')


def scene_steps(s, si, narr=None):
    _new_scene()
    P = f"s{si}"
    _reg(f"{P}-st-circ", "satu", "draw")
    hhtml, wids = _w3(s["baris"][0], si, "h")
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
        if _key(w) == "catat":
            _reg(wid, "catat", "emphasis", offset=0.1)
    _reg(f"{P}-st-line", "^", "draw", offset=1.0, dur=0.8)
    pts = [("Terima", "terima", "08:02", 160), ("Analisis", "analisis", "08:20", 460), ("Rilis", "rilis", "08:41", 760)]
    ptsvg = []
    for i, (lab, trig, tm, x) in enumerate(pts):
        _reg(f"{P}-st-pt{i}", trig, "pop")
        _reg(f"{P}-st-tm{i}", trig, "pop", offset=0.25)
        ptsvg.append(
            f'<g id="{P}-st-pt{i}" class="pop0"><circle class="ink" cx="{x}" cy="110" r="58" fill="#FBF9F4"/>'
            f'<text x="{x}" y="126" text-anchor="middle" font-size="34" font-family="Poppins" font-weight="700">{lab}</text></g>'
            f'<text id="{P}-st-tm{i}" class="pop0" x="{x}" y="215" text-anchor="middle" font-size="52" font-family="Caveat">{tm}</text>')
    _reg(f"{P}-st-strike", "tebakan", "draw", offset=0, dur=0.4)
    _reg(f"{P}-st-teb", "tebakan", "pop", offset=0.15)
    return (f'<div class="wrap" style="text-align:center">'
            f'<div style="display:flex;align-items:center;justify-content:center;gap:30px">'
            f'<svg viewBox="0 0 180 180" style="width:150px;flex:none" filter="url(#wobble)">'
            f'<circle class="ink draw" id="{P}-st-circ" pathLength="1" cx="90" cy="90" r="72"/>'
            f'<text x="90" y="125" text-anchor="middle" font-size="100" font-family="Caveat">1</text>{MARKER}</svg>'
            f'<p class="bar1" style="flex:1;min-width:0;max-width:700px">{hhtml}</p></div>'
            f'<svg viewBox="0 0 920 260" style="width:880px;margin:30px auto 0;display:block" filter="url(#wobble)">'
            f'<path class="ink draw" id="{P}-st-line" pathLength="1" d="M160 110 L760 110"/>'
            f'{"".join(ptsvg)}{MARKER}</svg>'
            f'<svg viewBox="0 0 640 130" style="width:560px;margin:16px auto 0;display:block" filter="url(#wobble)">'
            f'<text x="150" y="88" text-anchor="middle" font-size="76" font-family="Caveat">TAT</text>'
            f'<path class="ink-red draw" id="{P}-st-strike" pathLength="1" d="M40 62 L262 62"/>'
            f'<text id="{P}-st-teb" class="pop0" x="430" y="88" text-anchor="middle" font-size="76" font-family="Caveat" fill="#E5484D">tebakan?</text>'
            f'{MARKER}</svg>'
            f'<p class="bar2" style="margin-top:6px">{esc(s["baris"][1])}</p></div>')


def scene_dashboard(s, si, narr=None):
    _new_scene()
    P = f"s{si}"
    _reg(f"{P}-db-circ", "dua", "draw")
    _hl = s["baris"][0].replace("Pantau dashboard real-time",
                                "Pantau dashboard<br>real-time")
    hhtml, wids = _w3(_hl, si, "h")
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
    _reg(f"{P}-db-frame", "pantau", "draw", dur=0.7)
    _reg(f"{P}-db-head", "pantau", "pop", offset=0.4)
    cols = ["#34A853", "#34A853", "#FBBC04", "#FBBC04", "#E5484D", "#E5484D"]
    tubes = []
    for i in range(6):
        x = 150 + i * 115
        h = 110 + i * 42
        y = 430 - h
        _reg(f"{P}-db-tb{i}", "tumpukan", "drop", offset=i * 0.14)
        tubes.append(
            f'<g id="{P}-db-tb{i}" class="drop0"><rect x="{x}" y="{y}" width="88" height="{h}" rx="14" fill="{cols[i]}" opacity="0.85"/>'
            f'<rect class="ink" x="{x}" y="{y}" width="88" height="{h}" rx="14"/></g>')
    _reg(f"{P}-db-tb5", "jebol", "emphasis", offset=0.1)
    _reg(f"{P}-db-rcirc", "jebol", "draw", offset=0.15, dur=0.5)
    _reg(f"{P}-db-arrow", "kelihatan", "draw", offset=0.2, dur=0.5)
    _reg(f"{P}-db-cnt", "kelihatan", "countup", target=47, dur=2.0)
    return (f'<div class="wrap" style="text-align:center">'
            f'<div style="display:flex;align-items:center;justify-content:center;gap:30px">'
            f'<svg viewBox="0 0 180 180" style="width:150px;flex:none" filter="url(#wobble)">'
            f'<circle class="ink draw" id="{P}-db-circ" pathLength="1" cx="90" cy="90" r="72"/>'
            f'<text x="90" y="125" text-anchor="middle" font-size="100" font-family="Caveat">2</text>{MARKER}</svg>'
            f'<p class="bar1" style="flex:1;min-width:0;max-width:700px">{hhtml}</p></div>'
            f'<svg viewBox="0 0 920 560" style="width:880px;margin:24px auto 0;display:block" filter="url(#wobble)">'
            f'<rect class="ink draw" id="{P}-db-frame" pathLength="1" x="60" y="30" width="800" height="500" rx="26"/>'
            f'<text id="{P}-db-head" class="pop0" x="110" y="105" font-size="52" font-family="Poppins" font-weight="700">DASHBOARD LAB</text>'
            f'<text id="{P}-db-cnt" x="780" y="105" text-anchor="end" font-size="60" font-family="Caveat" fill="#E5484D">0</text>'
            f'{"".join(tubes)}'
            f'<ellipse class="ink-red draw" id="{P}-db-rcirc" pathLength="1" cx="770" cy="300" rx="85" ry="140"/>'
            f'<path class="ink-blue draw" id="{P}-db-arrow" pathLength="1" d="M700 120 A150 150 0 0 1 830 220 M800 195 L832 222 L800 248"/>'
            f'<text x="595" y="82" font-size="52" font-family="Caveat" fill="#1B5FD9" transform="rotate(-8 595 82)">numpuk!</text>'
            f'{MARKER}</svg></div>')


def scene_alarm(s, si, narr=None):
    _new_scene()
    P = f"s{si}"
    _reg(f"{P}-al-circ", "tiga", "draw")
    hhtml, wids = _w3(s["baris"][0], si, "h")
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
    _reg(f"{P}-al-bell", "pengingat", "swing", offset=0, svgOrigin="200 240", amp=10)
    _reg(f"{P}-al-bell", "pengingat", "emphasis", offset=0.15)
    _reg(f"{P}-al-swc", "^", "draw", offset=0.3, dur=0.6)
    _reg(f"{P}-al-arc", "lewat", "draw", offset=0, dur=0.8)
    _reg(f"{P}-al-hp", "peringatan", "pop")
    _reg(f"{P}-al-notif", "notif", "slideup", offset=0, sfx="ding")
    return (f'<div class="wrap" style="text-align:center">'
            f'<div style="display:flex;align-items:center;justify-content:center;gap:30px">'
            f'<svg viewBox="0 0 180 180" style="width:150px;flex:none" filter="url(#wobble)">'
            f'<circle class="ink draw" id="{P}-al-circ" pathLength="1" cx="90" cy="90" r="72"/>'
            f'<text x="90" y="125" text-anchor="middle" font-size="100" font-family="Caveat">3</text>{MARKER}</svg>'
            f'<p class="bar1" style="flex:1;min-width:0;max-width:700px">{hhtml}</p></div>'
            f'<svg viewBox="0 0 920 560" style="width:880px;margin:24px auto 0;display:block" filter="url(#wobble)">'
            f'<g id="{P}-al-bell"><path class="ink" d="M140 300 A60 60 0 0 1 260 300 L260 330 L140 330 Z" fill="#FBF9F4"/>'
            f'<circle class="ink" cx="200" cy="352" r="16" fill="#FBF9F4"/>'
            f'<line class="ink" x1="140" y1="300" x2="120" y2="280" stroke-width="7"/>'
            f'<line class="ink" x1="260" y1="300" x2="280" y2="280" stroke-width="7"/></g>'
            f'<circle class="ink draw" id="{P}-al-swc" pathLength="1" cx="470" cy="330" r="120"/>'
            f'<path class="ink-red draw" id="{P}-al-arc" pathLength="1" d="{_arc(470, 330, 130)}"/>'
            f'<g id="{P}-al-hp" class="pop0"><rect class="ink" x="600" y="140" width="190" height="340" rx="28" fill="#fff"/>'
            f'<rect class="ink" x="620" y="180" width="150" height="220" rx="10"/>'
            f'<circle class="ink" cx="695" cy="445" r="10"/></g>'
            f'<g id="{P}-al-notif" class="drop0"><rect x="545" y="55" width="270" height="115" rx="18" fill="#FFE45E" stroke="#1a1a1a" stroke-width="6"/>'
            f'<text x="680" y="100" text-anchor="middle" font-size="28" font-family="Poppins" font-weight="700">Sampel hampir</text>'
            f'<text x="680" y="135" text-anchor="middle" font-size="28" font-family="Poppins" font-weight="700">lewat batas TAT</text></g>'
            f'{MARKER}</svg></div>')


def scene_closing_stamp(s, si, narr=None):
    _new_scene()
    P = f"s{si}"
    thtml, wids = _w3(s["title"], si, "t")
    for wid, w in wids:
        _reg(wid, _key(w), "wordin")
    rows = []
    for i, it in enumerate(s["items"]):
        off = 0.8 + i * 0.8
        _reg(f"{P}-cs-b{i}", "^", "draw", offset=off, dur=0.4)
        _reg(f"{P}-cs-t{i}", "^", "pop", offset=off + 0.15)
        _reg(f"{P}-cs-c{i}", "^", "draw", offset=off + 0.35, dur=0.3, sfx="ding")
        rows.append(
            f'<div class="check" style="margin:22px 60px"><svg width="90" height="90" viewBox="0 0 90 90" filter="url(#wobble)">'
            f'<rect class="ink-blue draw" id="{P}-cs-b{i}" pathLength="1" x="8" y="8" width="74" height="74" rx="14"/>'
            f'<path class="ink-blue draw" id="{P}-cs-c{i}" pathLength="1" d="M22 46 L40 64 L70 28"/></svg>'
            f'<span id="{P}-cs-t{i}" class="pop0" style="font-size:64px">{esc(it)}</span></div>')
    _reg(f"{P}-cs-stamp", "jebol", "drop", offset=0.2)
    _reg(f"{P}-cs-shake", "jebol", "shake", offset=0.65, px=6)
    _reg(f"{P}-cs-rip", "jebol", "draw", offset=0.7, dur=0.6)
    _reg(f"{P}-cs-conf", "jebol", "confetti", offset=0.9)
    _reg(f"{P}-cs-push", "jebol", "campush", offset=0.7)
    _reg(f"{P}-cs-komen", "komen", "pop", offset=0.9)
    _reg(f"{P}-cs-arrow", "komen", "draw", offset=1.0, dur=0.4)
    _reg(f"{P}-cs-arrow", "komen", "idle", offset=1.5)
    return (f'<div class="wrap" style="text-align:center">'
            f'<h1 class="hand" style="font-size:96px">{thtml}</h1>'
            f'<div style="margin-top:24px">{"".join(rows)}</div>'
            f'<svg viewBox="0 0 700 300" style="width:640px;margin:10px auto 0;display:block" filter="url(#wobble)">'
            f'<g id="{P}-cs-stamp" class="drop0"><rect x="150" y="60" width="400" height="150" rx="30" style="fill:#1B5FD9;stroke:#1B5FD9;stroke-width:7;opacity:0.92" transform="rotate(-4 350 135)"/>'
            f'<text x="350" y="170" text-anchor="middle" font-size="88" font-family="Poppins" font-weight="800" fill="#fff" transform="rotate(-4 350 135)">FASTLIS</text></g>'
            f'<ellipse class="ink-blue draw" id="{P}-cs-rip" pathLength="1" cx="350" cy="135" rx="230" ry="105"/>'
            f'{MARKER}</svg>'
            f'<p id="{P}-cs-komen" class="pop0" style="font-family:Poppins,sans-serif;font-weight:700;font-size:52px;margin-top:10px">Komen: AMAN / JEBOL</p>'
            f'<svg viewBox="0 0 200 120" style="width:130px;margin:6px auto 0;display:block" filter="url(#wobble)">'
            f'<path class="ink-blue draw" id="{P}-cs-arrow" pathLength="1" d="M100 8 L100 88 M72 62 L100 92 L128 62"/>'
            f'{MARKER}</svg></div>')


BUILDERS = {"title": scene_title, "flow": scene_flow, "stage": scene_stage,
            "stamp": scene_stamp, "checklist": scene_checklist, "closing": scene_closing,
            "title_sw": scene_title_sw, "timeline": scene_timeline, "steps": scene_steps,
            "dashboard": scene_dashboard, "alarm": scene_alarm,
            "closing_stamp": scene_closing_stamp}


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
    _hl = re.search(r'class="blue"[^>]*>(.*?)</span>', d1.get("h1", ""), re.S)
    beats.append({
        "narr": n1,
        "scene": {"type": "title",
                  "title": d1.get("h1", ""),
                  "sub": strip_html(d1.get("sub", "")),
                  "ul_trigger": _pick_trigger(_hl.group(1) if _hl else n1)}})

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

    return assign_cams(beats)

# ------------------------------------------------- naskah .md (acuan pembuatan reels)
# Alur: --tulis-naskah (dari hari-ini.json) -> content/naskah-reels-YYYY-MM-DD.md
#       --daily baca .md itu (bisa diedit manual dulu); kalau tidak ada/rusak,
#       generate ulang dari hari-ini.json.

_CAM_DEF = {"title": "zin", "flow": "panr", "stage": "zin",
            "stamp": "zin", "checklist": "zout", "closing": "zout"}
_CAM_FLIP = {"zin": "zout", "zout": "zin", "panr": "panl", "panl": "panr"}
CAM_KE_MD = {"zin": "zoom-in", "zout": "zoom-out",
             "panr": "geser-kanan", "panl": "geser-kiri"}
CAM_DARI_MD = {v: k for k, v in CAM_KE_MD.items()}


def assign_cams(beats):
    """Isi b['cam'] yang kosong: default per tipe + jangan dua beat
    berurutan pakai gerakan yang sama. Cam eksplisit tidak diubah."""
    last = None
    for b in beats:
        c = b.get("cam")
        if not c:
            c = _CAM_DEF[b["scene"]["type"]]
            if c == last:
                c = _CAM_FLIP.get(c, c)
        b["cam"] = c
        last = c
    return beats


def daily_naskah_path(date=None):
    d = date or today_wib().strftime("%Y-%m-%d")
    return os.path.join(BASE, "content", f"naskah-reels-{d}.md")


def beats_to_md(beats, topik, date, variant=None, est_dur=None):
    """Beats -> markdown SPEC PRODUKSI: naskah + cara video dibuat.
    Bisa dibaca/diedit manual; field mesin: Judul/Sub/Narasi/Kotak/Baris/
    Item/Langkah/Atas/Cap/Kamera. Visual/Animasi/spec = dokumentasi."""
    assign_cams(beats)
    if variant is None:
        variant = JINGLE_VARIANTS[today_wib().timetuple().tm_yday % 4]
    L = [f"# Naskah Reels \u2014 {date}", f"Topik: {topik}", "",
         "## Spesifikasi produksi",
         "Gaya: whiteboard hand-drawn \u2014 kertas putih #FBF9F4 + pola titik, "
         "font Caveat (tulisan tangan), garis bergelombang, aksen biru FastLIS #1B5FD9",
         "Kanvas: 1080 x 1920 vertikal (9:16)",
         "Karaoke: kata yang sedang diucapkan disorot stabilo kuning #FFE45E, "
         "timing tiap kata asli dari whisper (bukan tebakan)",
         "Voice over: AI voice avocado_v2:MAI_01, Bahasa Indonesia",
         f"Musik latar: jingle FastLIS varian {variant} (volume 12%, "
         "fade in 1.5 dtk, fade out 2.5 dtk)",
         f"Durasi: \u00b1{est_dur or '?'} detik, {len(beats)} beat",
         "Aturan animasi: setiap elemen digambar/dimunculkan sinkron dengan kata "
         "yang diucapkan (bukan teks statis); kamera bergerak di tiap scene "
         "(lihat \"Kamera\" per beat); highlight simetris penuh",
         "Kamera boleh diisi: zoom-in / zoom-out / geser-kanan / geser-kiri",
         ""]
    for i, b in enumerate(beats, 1):
        s = b["scene"]
        t = s["type"]
        L.append(f"## Beat {i} \u2014 {t}")
        if t == "title":
            L += [f"Visual: judul besar tulisan tangan: "
                  f"\u201c{strip_html(s['title'])}\u201d"
                  + (f", sub kecil: \u201c{s.get('sub', '')}\u201d" if s.get("sub") else ""),
                  f"Animasi: judul pop-in; garis bawah digambar saat kata "
                  f"\u201c{s.get('ul_trigger') or '-'}\u201d diucapkan.",
                  f"Kamera: {CAM_KE_MD.get(b.get('cam'), b.get('cam'))}",
                  f"Judul: {s['title']}", f"Sub: {s.get('sub', '')}",
                  f"Narasi: {b['narr']}"]
        elif t == "stage":
            warna = "biru" if s.get("color") == "#1B5FD9" else "hitam"
            baris_txt = " / ".join(f"\u201c{d[0]}\u201d" for d in s["descs"])
            L += [f"Visual: kotak label \u201c{s['word']}\u201d ({warna}) + "
                  f"{len(s['descs'])} baris teks: {baris_txt}",
                  f"Animasi: kotak digambar saat kata "
                  f"\u201c{s.get('box_trigger') or '-'}\u201d diucapkan; "
                  f"tiap baris pop-in mengikuti narasi.",
                  f"Kamera: {CAM_KE_MD.get(b.get('cam'), b.get('cam'))}",
                  f"Kotak: {s['word']} | {warna}",
                  f"Baris: {' | '.join(d[0] for d in s['descs'])}",
                  f"Narasi: {b['narr']}"]
        elif t == "checklist":
            items_txt = ", ".join(f"\u201c{it[0]}\u201d" for it in s["items"])
            L += [f"Visual: judul \u201c{strip_html(s['title'])}\u201d + daftar "
                  f"centang ({len(s['items'])} item): {items_txt}",
                  "Animasi: tiap item pop-in dengan centang biru, sinkron narasi.",
                  f"Kamera: {CAM_KE_MD.get(b.get('cam'), b.get('cam'))}",
                  f"Judul: {s['title']}"]
            L += [f"Item: {it[0]}" for it in s["items"]]
            L += [f"Narasi: {b['narr']}"]
        elif t == "flow":
            L += [f"Visual: alur {len(s['steps'])} langkah: "
                  + " \u2192 ".join(s["steps"]),
                  "Animasi: tiap langkah + panah digambar berurutan mengikuti narasi.",
                  f"Kamera: {CAM_KE_MD.get(b.get('cam'), b.get('cam'))}",
                  f"Judul: {s['title']}",
                  f"Langkah: {' | '.join(s['steps'])}",
                  f"Narasi: {b['narr']}"]
        elif t == "stamp":
            L += [f"Visual: lingkaran peringatan + cap \u201c{s['stamp']}\u201d "
                  f"(atas: \u201c{s['top']}\u201d)",
                  f"Animasi: lingkaran digambar saat kata "
                  f"\u201c{s.get('circ_trigger') or '-'}\u201d; "
                  f"cap muncul dengan punch-zoom.",
                  f"Kamera: {CAM_KE_MD.get(b.get('cam'), b.get('cam'))}",
                  f"Atas: {s['top']}", f"Cap: {s['stamp']}",
                  f"Sub: {s.get('sub', '')}", f"Narasi: {b['narr']}"]
        elif t == "closing":
            L += ["Visual: kartu penutup: logo FastLIS + ajakan follow",
                  "Animasi: logo digambar; kamera zoom-out.",
                  f"Kamera: {CAM_KE_MD.get(b.get('cam'), b.get('cam'))}"]
            if s.get("title"):
                L += [f"Judul: {s['title']}"]
            if s.get("sub"):
                L += [f"Sub: {s['sub']}"]
            L += [f"Narasi: {b['narr']}"]
        else:
            L += [f"Narasi: {b['narr']}"]
        L.append("")
    return "\n".join(L).rstrip() + "\n"


def md_to_beats(path):
    """Parse .md naskah -> (date, beats). Raise ValueError kalau format rusak."""
    txt = open(path).read()
    m = re.search(r"^#{0,1}\s*(?:Naskah\s+)?Reels \u2014 (\d{4}-\d{2}-\d{2})", txt, re.M)
    if not m:
        raise ValueError("header '# Naskah Reels \u2014 YYYY-MM-DD' tidak ketemu")
    date = m.group(1)
    parts = re.split(r"^(?:##\s+)?Beat \d+ \u2014 (\w+)[^\n]*$", txt, flags=re.M)
    beats = []
    for j in range(1, len(parts), 2):
        t, body = parts[j], parts[j + 1]
        F, items = {}, []
        for line in body.strip().split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "Item":
                items.append(v)
            else:
                F[k] = v
        narr = F.get("Narasi", "")
        if not narr:
            raise ValueError(f"beat bertipe '{t}': field 'Narasi:' wajib ada")
        _kam = re.sub(r"\s*\(.*\)", "", F.get("Kamera", "")).strip().lower()
        cam = CAM_DARI_MD.get(_kam)
        beat = {"narr": narr, "scene": {}}
        if cam:
            beat["cam"] = cam
        _tr = re.search(r"T[1-5]", F.get("Transisi keluar", ""))
        if _tr:
            beat["trans"] = _tr.group(0)
        if t == "title":
            beat["scene"] = {"type": "title", "title": F.get("Judul", ""),
                             "sub": F.get("Sub", ""),
                             "ul_trigger": _pick_trigger(narr)}
        elif t == "stage":
            kot, _, warna = F.get("Kotak", " | hitam").partition("|")
            baris = [x.strip() for x in F.get("Baris", "").split("|") if x.strip()]
            beat["scene"] = {"type": "stage", "word": kot.strip(),
                             "color": "#1B5FD9" if warna.strip() == "biru" else "#1a1a1a",
                             "box_trigger": _pick_trigger(narr, kot.strip().lower()),
                             "descs": [[x, _pick_trigger(x)] for x in baris]}
        elif t == "checklist":
            beat["scene"] = {"type": "checklist", "title": F.get("Judul", ""),
                             "items": [[x, _pick_trigger(x)] for x in items]}
        elif t == "flow":
            beat["scene"] = {"type": "flow", "title": F.get("Judul", ""),
                             "steps": [x.strip() for x in F.get("Langkah", "").split("|")
                                       if x.strip()]}
        elif t == "stamp":
            beat["scene"] = {"type": "stamp", "top": F.get("Atas", ""),
                             "stamp": F.get("Cap", ""), "sub": F.get("Sub", ""),
                             "circ_trigger": _pick_trigger(narr),
                             "stamp_trigger": _pick_trigger(narr)}
        elif t == "closing":
            beat["scene"] = {"type": "closing", "title": F.get("Judul", ""),
                             "sub": F.get("Sub", "")}
        elif t == "title_sw":
            beat["scene"] = {"type": "title_sw", "title": F.get("Judul", ""),
                             "sub": F.get("Sub", "")}
        elif t in ("timeline", "steps", "dashboard", "alarm"):
            kot, _, warna = F.get("Kotak", " | hitam").partition("|")
            baris = [x.strip() for x in F.get("Baris", "").split("|") if x.strip()]
            beat["scene"] = {"type": t, "word": kot.strip(),
                             "color": "#1B5FD9" if warna.strip() == "biru" else "#1a1a1a",
                             "baris": baris}
        elif t == "closing_stamp":
            beat["scene"] = {"type": "closing_stamp", "title": F.get("Judul", ""),
                             "items": [x for x in items],
                             "stempel": F.get("Stempel", "FASTLIS")}
        else:
            raise ValueError(f"tipe scene '{t}' tidak dikenal")
        beats.append(beat)
    if not beats:
        raise ValueError("tidak ada beat yang bisa diparse")
    return date, beats


CSS = """
@font-face { font-family:'Caveat'; src:url('../assets/fonts/caveat-700.woff2') format('woff2'); font-weight:700; }
@font-face { font-family:'Poppins'; src:url('../assets/fonts/poppins-6.woff2') format('woff2'); font-weight:600; }
* { margin:0; padding:0; box-sizing:border-box; }
#root { width:1080px; height:1920px; position:relative; overflow:hidden;
  background:#FBF9F4; font-family:'Caveat',cursive; color:#1a1a1a; }
/* safe zone: x 80-1000, y 220-1450 */
.scene { position:absolute; inset:0; display:none; padding:220px 80px 470px 80px; }
.scene.on { display:block; }
.scene .dots { position:absolute; inset:-200px;
  background-image:radial-gradient(#00000010 1.5px, transparent 1.5px);
  background-size:28px 28px; }
.scene .wrap { position:absolute; inset:0; padding:220px 80px 470px 80px;
  display:flex; flex-direction:column; justify-content:center; }
.ink { stroke:#1a1a1a; stroke-width:7; fill:none; stroke-linecap:round; stroke-linejoin:round; }
.ink-red { stroke:#E5484D; stroke-width:9; fill:none; stroke-linecap:round; }
.ink-blue { stroke:#1B5FD9; stroke-width:7; fill:none; stroke-linecap:round; }
.draw { stroke-dasharray:1; stroke-dashoffset:1; }
h1.hand { font-size:110px; line-height:1.08; text-align:center; }
h1.hand .hl { background:linear-gradient(transparent 8%, #FFE45E 8%, #FFE45E 92%, transparent 92%); padding:0 14px; }
h1.hand .blue, .blue { color:#1B5FD9; }
h1.hand .red, .red { color:#E5484D; }
.sub { font-family:'Poppins',sans-serif; font-size:34px; color:#555; text-align:center; margin-top:18px; }
.bar1 { font-family:'Caveat',cursive; font-size:72px; text-align:center; line-height:1.15; }
.bar2 { font-family:'Caveat',cursive; font-size:60px; text-align:center; line-height:1.15; color:#333; }
.wrap { width:100%; }
.stagecard { display:flex; justify-content:center; }
.desclist { margin-top:34px; }
.checkline { display:flex; align-items:center; justify-content:center; gap:18px; margin:16px 0;
  font-family:'Poppins',sans-serif; font-size:36px; }
.checkline .dot { width:16px; height:16px; border-radius:50%; background:#1B5FD9; flex:none; }
.check { display:flex; align-items:center; gap:26px; margin:26px 60px; font-size:60px; }
.pill { display:inline-block; border:5px solid #1a1a1a; border-radius:999px;
  padding:18px 54px; font-size:56px; background:#fff; box-shadow:5px 5px 0 #1a1a1a22; }
#karaoke { position:absolute; left:80px; right:80px; top:1350px; min-height:220px;
  display:flex; align-items:center; justify-content:center; text-align:center; z-index:5; }
.chunk { font-family:'Poppins',sans-serif; font-weight:800; font-size:72px; line-height:1.35; color:#1a1a1a;
  background:#FFE45E; padding:8px 28px; border-radius:16px; display:inline-block; }
.rv { opacity:0; }
.pop0 { opacity:0; }
.drop0 { opacity:0; }
.w3 { opacity:0; display:inline-block; }
#brand { position:absolute; top:56px; left:70px; font-family:'Poppins',sans-serif;
  font-weight:800; font-size:34px; letter-spacing:2px; z-index:6; }
#brand b { color:#1B5FD9; }
#tracker { position:absolute; left:80px; top:250px; display:none; gap:18px; z-index:6; }
#tracker .tdot { width:34px; height:34px; border-radius:50%; border:5px solid #1a1a1a; background:#FBF9F4; }
#tracker .tdot.on { background:#1B5FD9; border-color:#1B5FD9; }
#fx { position:absolute; inset:0; pointer-events:none; z-index:20; }
.marker { opacity:0; }
.ripple { stroke:#1B5FD9; stroke-width:6; fill:none; opacity:0; }
"""


JS = """
var tl = gsap.timeline();
var TOTAL = __TOTAL__;
var BEAT_DURS = __BEATDURS__;
var BEAT_CAM = __BEATCAM__;
var CAM_DETAIL = __CAMDETAIL__;
var svgNS = 'http://www.w3.org/2000/svg';
/* ---------- karaoke chunk M6: 2-3 kata per chunk, swap sinkron narasi ---------- */
function showChunk(i) {
  document.querySelectorAll('.chunk').forEach(function(e){ e.style.display='none'; });
  var el = document.getElementById('c'+i);
  if(el){ el.style.display='inline-block';
    gsap.fromTo(el, {scale:0.7, opacity:0, y:24}, {scale:1, opacity:1, y:0, duration:0.28, ease:'back.out(2)'}); }
}
function clearChunks() {
  document.querySelectorAll('.chunk').forEach(function(e){ e.style.display='none'; });
}
/* ---------- M1 DRAW + spidol ---------- */
function drawEl(id, dur) {
  var el = document.getElementById(id); if(!el) return;
  dur = dur || 0.55;
  var svg = el.closest('svg'), marker = svg ? svg.querySelector('.marker') : null;
  var len = 1; try { len = el.getTotalLength(); } catch(e) {}
  var tw = gsap.fromTo(el, {strokeDashoffset:1}, {strokeDashoffset:0, duration:dur, ease:'power1.inOut',
    onStart: function(){
      if(marker){ marker.style.opacity=1;
        try { var pt0 = el.getPointAtLength(0); marker.setAttribute('transform','translate('+pt0.x+','+pt0.y+')'); } catch(e){} }
    },
    onUpdate: function(){
      if(!marker) return;
      try { var pt = el.getPointAtLength(len*tw.progress()); marker.setAttribute('transform','translate('+pt.x+','+pt.y+')'); } catch(e){}
    },
    onComplete: function(){
      if(!marker) return;
      var bb = svg.viewBox.baseVal;
      gsap.to(marker, {attr:{transform:'translate('+(bb.width+140)+','+(bb.height+140)+')'}, duration:0.35, ease:'power2.in',
        onComplete:function(){ marker.style.opacity=0; }});
    }});
}
/* ---------- M2 POP ---------- */
function popEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.timeline()
    .fromTo(el, {scale:0.5, y:30, rotation:-4, opacity:0, transformOrigin:'50% 50%'},
      {scale:1.15, y:0, rotation:0, opacity:1, duration:0.22, ease:'back.out(2)'})
    .to(el, {scale:1, duration:0.08, ease:'power1.inOut'});
}
/* ---------- M3 WORD-IN ---------- */
function wordIn(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {opacity:0, y:36}, {opacity:1, y:0, duration:0.18, ease:'power2.out'});
}
/* ---------- M4 IDLE ---------- */
function idleEl(id, dur) {
  var el = document.getElementById(id); if(!el) return;
  dur = dur || 4;
  gsap.to(el, {y:'+=6', duration:1, yoyo:true, repeat:Math.max(1,Math.round(dur)), ease:'sine.inOut', delay:0.6});
}
function spinEl(id, dur, speed, svgOrigin) {
  var el = document.getElementById(id); if(!el) return;
  var o = {rotation:'+=360', duration:speed||2.5, repeat:Math.ceil((dur||4)/(speed||2.5)), ease:'none'};
  if(svgOrigin) o.svgOrigin = svgOrigin; else o.transformOrigin = '50% 50%';
  gsap.to(el, o);
}
function swingEl(id, dur, amp, svgOrigin) {
  var el = document.getElementById(id); if(!el) return;
  var o = {duration:0.9, yoyo:true, repeat:Math.ceil((dur||4)/0.9), ease:'sine.inOut'};
  if(svgOrigin){ o.svgOrigin = svgOrigin; } else { o.transformOrigin = '50% 0%'; }
  gsap.fromTo(el, {rotation:-(amp||8)}, Object.assign({rotation:(amp||8)}, o));
}
/* ---------- M5 EMPHASIS ---------- */
function emphasisEl(id) {
  var el = document.getElementById(id); if(!el) return;
  var fx = document.getElementById('fxsvg');
  var r = el.getBoundingClientRect(), root = document.getElementById('root').getBoundingClientRect();
  var cx = r.left - root.left + r.width/2, cy = r.top - root.top + r.height/2;
  for(var i=0;i<5;i++){
    (function(i){
      var a = (i/5)*Math.PI*2 + 0.4;
      var x1 = cx + Math.cos(a)*(r.width/2+16), y1 = cy + Math.sin(a)*(r.height/2+16);
      var x2 = cx + Math.cos(a)*(r.width/2+52), y2 = cy + Math.sin(a)*(r.height/2+52);
      var ln = document.createElementNS(svgNS,'line');
      ln.setAttribute('x1',x1); ln.setAttribute('y1',y1);
      ln.setAttribute('x2',x1); ln.setAttribute('y2',y1);
      ln.setAttribute('stroke','#1B5FD9'); ln.setAttribute('stroke-width','7');
      ln.setAttribute('stroke-linecap','round');
      fx.appendChild(ln);
      gsap.to(ln, {attr:{x2:x2, y2:y2}, opacity:1, duration:0.16, delay:i*0.03,
        onComplete:function(){ gsap.to(ln,{opacity:0,duration:0.3,onComplete:function(){ln.remove();}}); }});
    })(i);
  }
  gsap.timeline()
    .to(el, {scale:1.18, duration:0.12, ease:'power2.out', transformOrigin:'50% 50%'}, 0)
    .to(el, {scale:1, duration:0.13, ease:'power2.inOut'}, 0.12)
    .to(el, {x:3, duration:0.04}, 0).to(el, {x:-3, duration:0.04}, 0.04).to(el, {x:0, duration:0.04}, 0.08);
}
function revealEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {opacity:0, y:26, scale:0.92}, {opacity:1, y:0, scale:1, duration:0.55, ease:'back.out(1.5)'});
}
function punch(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.timeline()
    .to(el, {scale:1.16, duration:0.22, ease:'power3.out', transformOrigin:'50% 50%'})
    .to(el, {scale:1.0, duration:0.5, ease:'back.out(1.6)'});
}
function dropEl(id) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {y:-260, opacity:0}, {y:0, opacity:1, duration:0.5, ease:'bounce.out'});
}
function shakeCam(px) {
  var w = document.querySelector('.scene.on .wrap'); if(!w) return;
  px = px || 6;
  gsap.timeline().to(w,{x:px,duration:0.05}).to(w,{x:-px,duration:0.05}).to(w,{x:px/2,duration:0.05}).to(w,{x:0,duration:0.05});
}
/* ---------- kamera: kontinu + drift + parallax ---------- */
function camera(si) {
  var wrap = document.querySelector('#s'+si+' .wrap');
  var dots = document.querySelector('#s'+si+' .dots');
  if(!wrap) return;
  var dur = BEAT_DURS[si]||8, kind = BEAT_CAM[si]||'zin', d = CAM_DETAIL[si]||{};
  gsap.set(wrap, {transformOrigin:'50% 50%'});
  var o = {duration:dur, ease:'power1.inOut'};
  var s0, s1, x0, x1, sc;
  if(kind==='zin'){ s0=d.s0||1; s1=d.s1||1.08; gsap.fromTo(wrap,{scale:s0},{scale:s1,...o}); }
  else if(kind==='zout'){ s0=d.s0||1.08; s1=d.s1||1.0; gsap.fromTo(wrap,{scale:s0},{scale:s1,...o}); }
  else { x0=(d.x0!==undefined?d.x0:(kind==='panr'?-55:55)); x1=(d.x1!==undefined?d.x1:(kind==='panr'?55:-55));
    var ps0=(d.s0!==undefined?d.s0:(d.s||1.04)), ps1=(d.s1!==undefined?d.s1:(d.s||1.04));
    gsap.fromTo(wrap,{x:x0,scale:ps0},{x:x1,scale:ps1,...o}); }
  if(dots){
    gsap.set(dots,{transformOrigin:'50% 50%'});
    var o2={duration:dur, ease:'power1.inOut'};
    if(kind==='zin'||kind==='zout'){ gsap.fromTo(dots,{scale:s0},{scale:(s0+s1)/2,...o2}); }
    else { gsap.fromTo(dots,{x:x0/2,scale:ps0},{x:x1/2,scale:(ps0+ps1)/2,...o2}); }
  }
  gsap.fromTo(wrap, {rotation:-0.4}, {rotation:0.4, duration:1.5, yoyo:true,
    repeat:Math.ceil(dur/1.5), ease:'sine.inOut'});
}
/* ---------- transisi T1-T5 ---------- */
function showScene(si) {
  document.querySelectorAll('.scene').forEach(function(e){ e.classList.remove('on'); });
  var el = document.getElementById('s'+si); if(el) el.classList.add('on');
  camera(si);
}
function transEl(kind, nextSi){
  var fx = document.getElementById('fx'), fxs = document.getElementById('fxsvg');
  if(kind==='T1'){
    var c = document.createElement('div');
    c.style.cssText='position:absolute;left:50%;top:42%;width:140px;height:140px;margin:-70px;border:8px solid #1a1a1a;border-radius:50%;background:#FBF9F4;';
    fx.appendChild(c);
    gsap.to(c,{scale:17,duration:0.25,ease:'power2.in',onComplete:function(){
      showScene(nextSi); gsap.to(c,{opacity:0,duration:0.15,onComplete:function(){c.remove();}}); }});
  } else if(kind==='T2'){
    var w = document.createElement('div');
    w.style.cssText='position:absolute;top:0;bottom:0;left:1080px;width:1080px;background:#FBF9F4;box-shadow:-24px 0 48px rgba(0,0,0,.18);';
    fx.appendChild(w);
    gsap.to(w,{x:-1080,duration:0.2,ease:'power3.in',onComplete:function(){
      showScene(nextSi);
      gsap.to(w,{x:-2160,duration:0.22,ease:'power3.out',onComplete:function(){w.remove();}}); }});
  } else if(kind==='T3'){
    var p = document.createElementNS(svgNS,'path');
    p.setAttribute('d','M-60 260 L1140 460 L-60 660 L1140 860 L-60 1060 L1140 1260 L-60 1460 L1140 1660');
    p.setAttribute('stroke','#1a1a1a'); p.setAttribute('stroke-width','70'); p.setAttribute('fill','none');
    p.setAttribute('stroke-linecap','round'); fxs.appendChild(p);
    var len = p.getTotalLength();
    gsap.fromTo(p,{strokeDasharray:len,strokeDashoffset:len},{strokeDashoffset:0,duration:0.25,ease:'power2.in',onComplete:function(){
      showScene(nextSi);
      gsap.to(p,{y:-1920,duration:0.16,ease:'power2.in',onComplete:function(){p.remove();}}); }});
  } else if(kind==='T4'){
    var f = document.createElement('div');
    f.style.cssText='position:absolute;inset:0;background:#fff;opacity:0;'; fx.appendChild(f);
    gsap.to(f,{opacity:1,duration:0.08,onComplete:function(){
      showScene(nextSi);
      for(var i=0;i<8;i++){ (function(i){
        var a=(i/8)*Math.PI*2, ln=document.createElementNS(svgNS,'line');
        var cx=540, cy=960;
        ln.setAttribute('x1',cx); ln.setAttribute('y1',cy); ln.setAttribute('x2',cx); ln.setAttribute('y2',cy);
        ln.setAttribute('stroke','#E5484D'); ln.setAttribute('stroke-width','10'); ln.setAttribute('stroke-linecap','round');
        fxs.appendChild(ln);
        gsap.to(ln,{attr:{x2:cx+Math.cos(a)*320, y2:cy+Math.sin(a)*320}, opacity:0, duration:0.4, ease:'power2.out',
          onComplete:function(){ln.remove();}});
      })(i); }
      gsap.to(f,{opacity:0,duration:0.2,onComplete:function(){f.remove();}}); }});
  } else if(kind==='T5'){
    var cur = document.querySelector('.scene.on .wrap');
    var ns = document.getElementById('s'+nextSi); ns.classList.add('on');
    var nxt = ns.querySelector('.wrap');
    var sh = document.createElement('div');
    sh.style.cssText='position:absolute;left:0;right:0;top:0;height:120px;background:linear-gradient(rgba(0,0,0,.22),transparent);opacity:0;';
    fx.appendChild(sh);
    gsap.set(nxt,{y:1920}); camera(nextSi);
    gsap.to(sh,{opacity:1,duration:0.1});
    gsap.to(cur,{y:-1920,duration:0.4,ease:'power2.inOut'});
    gsap.to(nxt,{y:0,duration:0.4,ease:'power2.inOut',onComplete:function(){
      document.querySelectorAll('.scene').forEach(function(e){ if(e.id!=='s'+nextSi) e.classList.remove('on'); });
      gsap.set([cur,nxt],{y:0}); sh.remove(); }});
  } else { showScene(nextSi); }
}
function slideX(id, x, dur) {
  var el = document.getElementById(id); if(!el) return;
  gsap.to(el, {x:x, duration:dur||1, ease:'power1.inOut'});
}
function slideUpEl(id, dist) {
  var el = document.getElementById(id); if(!el) return;
  gsap.fromTo(el, {y:dist||80, opacity:0}, {y:0, opacity:1, duration:0.4, ease:'back.out(1.4)'});
}
function countUp(id, target, dur) {
  var el = document.getElementById(id); if(!el) return;
  var o = {v:0};
  gsap.to(o, {v:target, duration:dur||1.5, ease:'power1.out',
    onUpdate:function(){ el.textContent = Math.round(o.v); }});
}
function confettiBurst() {
  var fxs = document.getElementById('fxsvg');
  for(var i=0;i<24;i++){ (function(i){
    var ln = document.createElementNS(svgNS,'line');
    var x = 200+Math.random()*680, y = 480+Math.random()*420;
    ln.setAttribute('x1',x); ln.setAttribute('y1',y); ln.setAttribute('x2',x); ln.setAttribute('y2',y);
    ln.setAttribute('stroke', i%3 ? '#1B5FD9' : '#E5484D'); ln.setAttribute('stroke-width','9');
    ln.setAttribute('stroke-linecap','round');
    fxs.appendChild(ln);
    gsap.to(ln, {attr:{x2:x+(Math.random()*180-90), y2:y+(Math.random()*180-90)}, opacity:0,
      duration:0.9, delay:Math.random()*0.3, ease:'power2.out', onComplete:function(){ln.remove();}});
  })(i); }
}
function camPush(si) {
  var w = document.querySelector('#s'+si+' .wrap'); if(!w) return;
  gsap.to(w, {scale:1.04, duration:0.35, ease:'power2.out'});
}
/* ---------- progress tracker ---------- */
function trackerDot(n){
  var tr = document.getElementById('tracker');
  if(n<0){ tr.style.display='none'; return; }
  tr.style.display='flex';
  tr.querySelectorAll('.tdot').forEach(function(d,i){ d.classList.toggle('on', i===n); });
}
/* ---------- garis boil 8fps ---------- */
(function(){
  var turb = document.getElementById('boilTurb'); if(!turb) return;
  var iv = setInterval(function(){ turb.setAttribute('seed', Math.floor(Math.random()*90)+5); }, 125);
  setTimeout(function(){ clearInterval(iv); }, (TOTAL+2)*1000);
})();
__CALLS__
"""



def build_from_beats(beats, prefix="whiteboard"):
    """Bangun VO + timing karaoke + HTML whiteboard dari daftar beats generik.

    beats: list of {"narr": str, "scene": {"type": ..., ...}}
    Output: reels/v2/<prefix>.html, vo_<prefix>.mp3, timings_<prefix>.json
    """
    assign_cams(beats)
    # ---- TTS per beat + jeda 0.2 dtk antar beat (spec produksi) ----
    import wave
    narr_text = "\n".join(b["narr"] for b in beats)
    vo_path = os.path.join(V2, f"vo_{prefix}.mp3")
    open(os.path.join(V2, f"vo_{prefix}.txt"), "w").write(narr_text)
    segs, sr, nch, sw = [], None, 1, 2
    for bi, b in enumerate(beats):
        tmp = os.path.join(V2, f"_vo_{prefix}_{bi}.wav")
        cp = subprocess.run([TTS, "speak", "--language", "id", "--voice", VOICE,
                             "--format", "wav", "--output", tmp,
                             "--text-stdin"],
                            input=b["narr"].encode(), capture_output=True)
        if cp.returncode != 0 or not os.path.exists(tmp):
            print("TTS GAGAL:", cp.stderr.decode()[:500]); sys.exit(1)
        d = open(tmp, "rb").read()
        d = d[d.find(b"RIFF"):]  # buang junk bytes CLI
        open(tmp, "wb").write(d)
        w = wave.open(tmp, "rb")
        if sr is None:
            sr, nch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        segs.append(w.readframes(w.getnframes()))
        w.close()
        os.remove(tmp)
    gap = b"\x00" * int(sr * 0.2) * nch * sw
    pcm = gap.join(segs)
    vo_wav = os.path.join(V2, f"vo_{prefix}.wav")
    w = wave.open(vo_wav, "wb")
    w.setnchannels(nch); w.setsampwidth(sw); w.setframerate(sr)
    w.writeframes(pcm); w.close()
    cp = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vo_wav,
                         "-c:a", "libmp3lame", "-b:a", "128k", vo_path],
                        capture_output=True)
    if cp.returncode != 0:
        print("konversi mp3 GAGAL"); sys.exit(1)
    dur = audio_duration(vo_path)
    total = round(dur + 2.5, 2)  # tail hold: CTA akhir butuh napas ±2 dtk
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
        scene_divs.append(f'<div class="scene" id="s{si}"><div class="dots"></div>{fn(b["scene"], si, b["narr"])}</div>')

    # ---- karaoke: DINONAKTIFKAN per 2026-10-19 (permintaan Adri) ----
    # (chunk_divs + showChunk dihapus; timing kata tetap dipakai untuk trigger animasi)
    print(f"karaoke: nonaktif ({len(words)} kata)")

    calls = []
    sfx = []  # (t, nama)
    _SFX_KIND = {"draw": "scribble", "pop": "pop", "emphasis": "pop",
                 "drop": "pop", "slideup": "pop"}
    _JSFN = {"draw": "drawEl", "pop": "popEl", "wordin": "wordIn",
             "idle": "idleEl", "spin": "spinEl", "swing": "swingEl",
             "emphasis": "emphasisEl", "reveal": "revealEl", "punch": "punch",
             "drop": "dropEl", "slidex": "slideX", "slideup": "slideUpEl",
             "countup": "countUp", "confetti": "confettiBurst",
             "shake": "shakeCam", "campush": "camPush"}
    skip_show = set()
    for bi, b in enumerate(beats):
        if b.get("trans") and bi + 1 < len(beats):
            skip_show.add(bi + 1)
    for bi, (a, bb) in enumerate(bounds):
        if bi not in skip_show:
            calls.append(f'tl.call(showScene, [{bi}], {a});')
        if bi in (2, 3, 4):
            calls.append(f'tl.call(trackerDot, [{bi - 2}], {a});')
        wmap = {}
        for wd in words:
            if a - 0.01 <= wd["t0"] <= bb + 0.01:
                wmap.setdefault(_key(wd["w"]), wd["t0"])
        regs = _draw_ids[bi]
        n = len(regs)
        for k, r in enumerate(regs):
            trig = r["trigger"]
            if trig == "^":
                t = a
            elif trig:
                t = wmap.get(_key(trig))
            else:
                t = None
            if t is None:
                t = a + (bb - a) * (0.12 + 0.76 * (k + 1) / (n + 1))
            t = round(t + r["offset"], 3)
            fn = _JSFN[r["kind"]]
            eid = r["id"]
            if r["kind"] == "draw":
                calls.append(f"tl.call({fn}, ['{eid}', {r.get('dur', 0.55)}], {t});")
            elif r["kind"] in ("idle", "spin", "swing"):
                _so = f", '{r['svgOrigin']}'" if r.get("svgOrigin") else ""
                calls.append(f"tl.call({fn}, ['{eid}', {round(bb - a, 2)}{_so}], {t});")
            elif r["kind"] == "slidex":
                calls.append(f"tl.call({fn}, ['{eid}', {r.get('x', 0)}, {r.get('dur', 1)}], {t});")
            elif r["kind"] == "countup":
                calls.append(f"tl.call({fn}, ['{eid}', {r.get('target', 10)}, {r.get('dur', 1.5)}], {t});")
            elif r["kind"] == "confetti":
                calls.append(f"tl.call({fn}, [], {t});")
            elif r["kind"] == "shake":
                calls.append(f"tl.call({fn}, [{r.get('px', 6)}], {t});")
            elif r["kind"] == "campush":
                calls.append(f"tl.call({fn}, [{bi}], {t});")
            else:
                calls.append(f"tl.call({fn}, ['{eid}'], {t});")
            sn = r.get("sfx", _SFX_KIND.get(r["kind"]))
            if sn:
                sfx.append((t, sn))
        tr = beats[bi].get("trans")
        if tr and bi + 1 < len(beats):
            tt = round(bb - 0.4, 3)
            calls.append(f"tl.call(transEl, ['{tr}', {bi + 1}], {tt});")
            sfx.append((tt, "swoosh"))
        if beats[bi]["scene"]["type"] == "title_sw":
            tk = a + 0.3
            while tk < min(bb, a + 3.2):
                sfx.append((round(tk, 3), "tick"))
                tk += 0.5
    calls.append(f'tl.call(clearChunks, [], {total - 0.05});')
    calls.append(f'tl.call(trackerDot, [-1], {total - 0.05});')
    sfx.sort()
    json.dump([{"t": t, "sfx": n} for t, n in sfx],
              open(os.path.join(V2, f"sfx_{prefix}.json"), "w"))

    beat_durs = [round(bb - a, 2) for a, bb in bounds]
    cam = {"title": "zin", "flow": "panr", "stage": "zin", "stamp": "zin",
           "checklist": "zout", "closing": "zout"}
    beat_cams = [b.get("cam") or cam[b["scene"]["type"]] for b in beats]
    _CAMDTL = {"title_sw": {"s0": 1.0, "s1": 1.25},
               "timeline": {"s0": 1.3, "s1": 1.0},
               "steps": {"x0": 0, "x1": -80, "s0": 1.05, "s1": 1.12},
               "dashboard": {"s0": 1.0, "s1": 1.35},
               "alarm": {"x0": 0, "x1": 80, "s0": 1.1, "s1": 1.2},
               "closing_stamp": {"s0": 1.25, "s1": 1.0}}
    cam_detail = [_CAMDTL.get(b["scene"]["type"], {}) for b in beats]
    js = JS.replace("__BEATDURS__", json.dumps(beat_durs)).replace(
        "__BEATCAM__", json.dumps(beat_cams)).replace(
        "__CAMDETAIL__", json.dumps(cam_detail)).replace(
        "__TOTAL__", str(total)).replace(
        "__CALLS__", "\n".join(calls))

    html = (f'<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">'
            f'<style>{CSS}</style></head><body>'
            f'<div id="root" data-composition-id="whiteboard" data-start="0" '
            f'data-duration="{total}" data-width="1080" data-height="1920" data-fps="30">'
            f'<div id="brand">FAST<b>LIS</b></div>{WOBBLE}'
            f'<div id="tracker"><span class="tdot"></span><span class="tdot"></span><span class="tdot"></span></div>'
            f'<div id="fx"><svg id="fxsvg" width="1080" height="1920"></svg></div>'
            f'{"".join(scene_divs)}'
            f'</div>'
            f'<script src="../assets/gsap.min.js"></script><script>{js}</script>'
            f'</body></html>')
    open(os.path.join(V2, f"{prefix}.html"), "w").write(html)
    print(f"{prefix}.html ditulis ({total}s), {len(beats)} scene")


def main():
    beats, prefix = BEATS, "whiteboard"
    args = sys.argv[1:]
    if "--tulis-naskah" in args:
        date = today_wib().strftime("%Y-%m-%d")
        _np = daily_naskah_path(date)
        if os.path.exists(_np) and "--force" not in args:
            print(f"naskah sudah ada: {_np} (tidak ditimpa; pakai --force untuk timpa)")
            return
        topik = json.load(open(os.path.join(BASE, "content", "hari-ini.json")))["topik"]
        beats = compose_daily_beats()
        p = daily_naskah_path(date)
        doy = today_wib().timetuple().tm_yday
        narr_chars = len(" ".join(b["narr"] for b in beats))
        est = round(max(1, narr_chars) / 850 * 60)
        open(p, "w").write(beats_to_md(beats, topik, date,
                                       variant=JINGLE_VARIANTS[doy % 4],
                                       est_dur=est))
        print(f"naskah ditulis: {p} ({len(beats)} beats)")
        return
    daily = "--daily" in args
    if daily:
        prefix = "daily"
        p = daily_naskah_path()
        if os.path.exists(p):
            try:
                d, beats = md_to_beats(p)
                if d != today_wib().strftime("%Y-%m-%d"):
                    raise ValueError(f"tanggal naskah {d} bukan hari ini")
                print(f"mode daily: {len(beats)} beats dari {p} (acuan .md)")
            except ValueError as e:
                print(f"naskah rusak ({e}), generate ulang dari hari-ini.json")
                p = None
        if not os.path.exists(p or ""):
            beats = compose_daily_beats()
            topik = json.load(open(os.path.join(BASE, "content", "hari-ini.json")))["topik"]
            p = daily_naskah_path()
            open(p, "w").write(beats_to_md(beats, topik, today_wib().strftime("%Y-%m-%d")))
            print(f"mode daily: {len(beats)} beats dari content/hari-ini.json (+ naskah ditulis)")
    elif "--beats" in args:
        i = args.index("--beats")
        beats = json.load(open(args[i + 1]))
        if "--prefix" in args:
            prefix = args[args.index("--prefix") + 1]
        print(f"mode beats-file: {len(beats)} beats, prefix={prefix}")
    build_from_beats(beats, prefix)
    if daily:
        # paritas dengan builder v2 supaya langkah cron 2 & 5 tidak berubah
        doy = today_wib().timetuple().tm_yday
        print(f"VARIANT={JINGLE_VARIANTS[doy % 4]}")
        write_status("siap-render", 100, "daily.html siap dirender")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 4 and args[0] == "--mux":
        # --mux <render_mp4> <vo_mp3> <out_mp4> ; varian dari VARIANT hari ini
        doy = today_wib().timetuple().tm_yday
        sys.exit(mux(args[1], args[2], args[3], JINGLE_VARIANTS[doy % 4]))
    main()
