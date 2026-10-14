#!/usr/bin/env python3
"""Pipeline reels FastLIS v2 sinematik (template harian).

Alur: baca content/hari-ini.json key "reels" (s1..s6)
  -> susun narasi VO per beat -> TTS (id) -> estimasi timing karaoke
  -> pilih foto per beat -> tulis reels/v2/daily.html

Render:  cd reels && TMPDIR=$PWD/.tmp npx hyperframes render -c v2/daily.html -o <out>
Mux:     ffmpeg -i <render> -i v2/vo_daily.mp3 -i assets/jingle-<varian>.wav
         -filter_complex "[1:a]volume=1.0[vo];[2:a]volume=0.12,afade...[bg];
                          [vo][bg]amix=inputs=2:duration=longest[a]"
         -map 0:v -map "[a]" -c:v copy -c:a aac -movflags +faststart <final>

Varian jingle rotasi harian: dayofyear % 4 -> original/chill/energetic/minimal.
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys

BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
V2 = os.path.join(BASE, "reels", "v2")
ASSETS = os.path.join(BASE, "reels", "assets")
JSON_P = os.path.join(BASE, "content", "hari-ini.json")
VO_OUT = os.path.join(V2, "vo_daily.mp3")
HTML_OUT = os.path.join(V2, "daily.html")
TTS = "/opt/hatch/bin/tts"
VOICE = "avocado_v2:MAI_01"
JINGLE_VARIANTS = ["original", "chill", "energetic", "minimal"]


def today_wib():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7)))


def strip_html(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", s).strip()


def blue_to_hl(s):
    return s.replace('class="blue"', 'class="hl"')


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


def compute_timings(beats, total):
    words = []
    for bi, b in enumerate(beats):
        for w in b["narr"].split(" "):
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


LAB_KEYS = {"lab", "tabung", "sampel", "mikroskop", "analyzer", "pipet", "reagen",
            "darah", "serum", "sentrifug", "qc", "pre-analitik", "analitik", "alat",
            "tube", "laboratorium"}
# file yang sudah diverifikasi BUKAN foto lab (cek visual langsung)
PHOTO_DENY = {"lab-09.jpg", "lab-10.jpg", "lab-11.jpg", "lab-12.jpg"}


def _is_lab_photo(fn, tags):
    if fn in PHOTO_DENY:
        return False
    tg = [str(x).lower() for x in tags.get(fn, [])]
    if "bukan foto lab" in tg:
        return False
    return any(k in t for t in tg for k in LAB_KEYS)


def pick_photos(beats_kw, dayofyear, ignore_used=False):
    """Pilih foto per beat berdasarkan relevansi tag; unik antar beat; hindari yang baru dipakai."""
    cands = sorted(glob.glob(os.path.join(ASSETS, "lab-*.jpg")))
    cands = [os.path.basename(c) for c in cands]
    try:
        tags = json.load(open(os.path.join(BASE, "data", "photo_tags.json")))
        cands = [c for c in cands if _is_lab_photo(c, tags)]
    except Exception:
        tags = {}
    used = set()
    if not ignore_used:
        try:
            uj = json.load(open(os.path.join(BASE, "data", "used_images.json")))
            used.update(uj.get("today_video", []))
        except Exception:
            pass

    def score(fn, kws):
        tg = " ".join(str(x).lower() for x in tags.get(fn, []))
        return sum(1 for k in kws if k in tg)

    def stable(fn):
        return (sum(ord(ch) for ch in fn) + dayofyear) % 997

    picks = []
    for kws in beats_kw:
        ranked = sorted((c for c in cands if c not in used and c not in picks),
                        key=lambda c: (-score(c, kws), stable(c)))
        if not ranked:
            ranked = sorted((c for c in cands if c not in picks),
                            key=lambda c: (-score(c, kws), stable(c)))
        picks.append(ranked[0] if ranked else cands[0])
    return picks


# keyword relevansi foto per beat: s1 hook, s2 konteks, s3 hemolisis, s4 lipemia, s5 ikterus
BEAT_KW = [
    ["serum", "tabung", "sampel", "darah"],
    ["pre-analitik", "tabung", "pengambilan", "sampel"],
    ["pengambilan", "pipet", "tabung darah", "pre-analitik"],
    ["serum", "tabung", "sampel", "rak"],
    ["serum", "tabung", "sampel", "reagen"],
]


def main():
    d = json.load(open(JSON_P))
    r = d.get("reels")
    if not r:
        print("tidak ada key 'reels' di hari-ini.json")
        return 1
    t = today_wib()
    doy = t.timetuple().tm_yday

    # ---- susun beats ----
    beats = []
    # s1: hook
    d1 = r.get("s1", {})
    beats.append({
        "label": f"BAGIAN 01 &middot; {esc(strip_html(d1.get('kicker', '')).upper())}",
        "title": blue_to_hl(d1.get("h1", "")),
        "narr": join_spoken(strip_html(d1.get('h1', '')), strip_html(d1.get('sub', ''))),
        "key": strip_html(d1.get('sub', '')),
        "bg": d1.get("bg", ""),
    })
    # s2: konteks
    d2 = r.get("s2", {})
    beats.append({
        "label": f"BAGIAN 02 &middot; {esc(strip_html(d2.get('kicker', '')).upper())}",
        "title": blue_to_hl(d2.get("h1", "")),
        "narr": join_spoken(strip_html(d2.get('h1', '')), strip_html(d2.get('sub', ''))),
        "key": strip_html(d2.get('sub', '')),
        "bg": d2.get("bg", ""),
    })
    # s3-s5: poin
    for i, key in enumerate(("s3", "s4", "s5"), start=3):
        dd = r.get(key, {})
        beats.append({
            "label": f"BAGIAN 0{i} &middot; {esc(strip_html(dd.get('sub', '')).upper())}",
            "title": blue_to_hl(dd.get("title", "")),
            "narr": join_spoken(strip_html(dd.get('title', '')), strip_html(dd.get('sub', '')),
                         strip_html(dd.get('desc', ''))),
            "key": strip_html(dd.get('desc', '')),
            "bg": dd.get("bg", ""),
        })
    # s6: penutup
    d6 = r.get("s6", {})
    pills = "".join(f'<span class="pill">{esc(p)}</span>' for p in d6.get("pills", [])[:3])
    beats.append({
        "label": "PENUTUP",
        "title": blue_to_hl(d6.get("h1", "")),
        "narr": join_spoken(strip_html(d6.get('h1', '')), strip_html(d6.get('sub', ''))),
        "bg": "",
        "pills": pills,
        "ask_sub": strip_html(d6.get("sub", "")),
    })

    return build_from_beats(beats, "daily", doy, track=True)


def build_from_beats(beats, prefix, doy, track=True, ignore_used=False):
    """Pipeline generik: foto -> TTS -> timing -> html. prefix: daily/long."""
    t = today_wib()

    # ---- foto per beat (kecuali penutup) ----
    auto = pick_photos([b.get("kw") or BEAT_KW[i % len(BEAT_KW)]
                        for i, b in enumerate(beats[:-1])], doy,
                        ignore_used=ignore_used)
    ai = 0
    for b in beats[:-1]:
        bg = b.get("bg", "")
        base = os.path.basename(bg) if bg else ""
        ok = base.startswith("lab-") and os.path.exists(os.path.join(ASSETS, base))
        if ok:
            b["photo"] = f"../assets/{base}"
        else:
            b["photo"] = f"../assets/{auto[ai]}"
            ai += 1

    # ---- TTS ----
    narr_text = "\n".join(b["narr"] for b in beats)
    open(os.path.join(V2, f"vo_{prefix}.txt"), "w").write(narr_text)
    print("naskah VO:", narr_text[:120], "...")
    cp = subprocess.run([TTS, "speak", "--language", "id", "--voice", VOICE,
                         "--output", os.path.join(V2, f"vo_{prefix}.mp3"), "--text-stdin"],
                        input=narr_text.encode(), capture_output=True)
    if cp.returncode != 0 or not os.path.exists(os.path.join(V2, f"vo_{prefix}.mp3")):
        print("TTS GAGAL:", cp.stderr.decode()[:500])
        return 1
    dur = audio_duration(os.path.join(V2, f"vo_{prefix}.mp3"))
    total = round(dur + 0.4, 2)
    print(f"VO jadi: {dur:.1f}s")

    words, bounds = compute_timings(beats, dur)
    json.dump({"words": words, "bounds": bounds, "total": total,
               "date": t.strftime("%Y-%m-%d")},
              open(os.path.join(V2, f"timings_{prefix}.json"), "w"), indent=1)

    # ---- HTML ----
    wi = 0
    karaoke_divs = []
    for bi, b in enumerate(beats):
        spans = [f'<span class="kw" id="w{wi + j}">{esc(w)}</span>'
                 for j, w in enumerate(b["narr"].split(" "))]
        wi += len(spans)
        karaoke_divs.append(
            f'<div class="phrase" id="p{bi}" style="display:none">{" ".join(spans)}</div>')

    calls = [f'tl.call(setWord, [{i}], {wd["t0"]});' for i, wd in enumerate(words)]
    for bi, (a, _) in enumerate(bounds):
        calls.append(f'tl.call(showPhrase, [{bi}], {a});')
    calls.append(f'tl.call(clearWords, [], {total - 0.05});')

    beat_divs, trans = [], []
    for bi, b in enumerate(beats):
        if "pills" in b:  # penutup
            q = b["ask_sub"]
            vis = (f'<div class="card ask" id="b{bi}-vis">'
                   f'<div class="big">{esc(q)}</div>'
                   f'<div class="pillrow">{b["pills"]}</div></div>')
        else:
            cap = strip_html(b["title"]).split("?")[0][:48]
            vis = (f'<div class="polaroid" id="b{bi}-vis"><div class="tape"></div>'
                   f'<img src="{b["photo"]}"><div class="cap">{esc(cap)}</div></div>'
                   f'<div class="keystrip" id="b{bi}-key"><span class="kdot"></span>{esc(b.get("key",""))}</div>')
        op = "" if bi == 0 else ' style="opacity:0"'
        beat_divs.append(
            f'<div class="beat" id="beat{bi}"{op}>'
            f'<div class="chlabel">{b["label"]}</div>'
            f'<div class="bigt">{b["title"]}</div>{vis}</div>')
        if bi > 0:
            t_in = round(bounds[bi][0] - 0.45, 2)
            trans.append(f'tl.to("#beat{bi-1}", {{opacity:0, y:-70, duration:.35, ease:"power2.in"}}, {t_in});')
            trans.append(f'tl.fromTo("#beat{bi}", {{opacity:0, y:70}}, {{opacity:1, y:0, duration:.5, ease:"power2.out"}}, {round(t_in + 0.18, 2)});')
            trans.append(f'tl.from("#beat{bi} .chlabel", {{opacity:0, y:14, duration:.45}}, {round(t_in + .15, 2)});')
            trans.append(f'tl.from("#beat{bi} .bigt", {{opacity:0, y:26, duration:.6}}, {round(t_in + .3, 2)});')
            trans.append(f'tl.from("#b{bi}-vis", {{opacity:0, y:22, scale:.97, duration:.55}}, {round(t_in + .55, 2)});')
            trans.append(f'tl.from("#b{bi}-key", {{opacity:0, x:-18, duration:.45}}, {round(t_in + .8, 2)});')

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
  #canvas{{position:absolute;inset:-70px;background:radial-gradient(rgba(120,175,230,.13) 2px, transparent 2.6px);background-size:36px 36px;}}
  #vignette{{position:absolute;inset:0;z-index:2;background:radial-gradient(ellipse 90% 70% at 50% 42%, transparent 40%, rgba(2,8,18,.80) 100%);}}
  .progress{{position:absolute;top:0;left:0;height:8px;width:0;background:#0469DC;z-index:5}}
  .beat{{position:absolute;inset:0;z-index:3;display:flex;flex-direction:column;justify-content:center;padding:40px 72px 360px}}
  .chlabel{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:27px;letter-spacing:5px;color:#3B9EFF;font-weight:700}}
  .bigt{{font-size:84px;font-weight:800;color:#fff;line-height:1.04;letter-spacing:-2px;margin-top:24px;text-transform:uppercase}}
  .bigt .hl{{color:#3B9EFF}}
  .polaroid{{margin-top:34px;background:#fff;border-radius:10px;padding:18px 18px 0;transform:rotate(-2deg);box-shadow:0 24px 60px rgba(0,0,0,.45);position:relative}}
  .polaroid img{{width:100%;height:600px;object-fit:cover;object-position:center 72%;display:block;border-radius:4px}}
  .polaroid .cap{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:25px;color:#334155;padding:18px 6px;letter-spacing:1px}}
  .polaroid .tape{{position:absolute;top:-22px;left:50%;width:180px;height:44px;background:rgba(230,236,245,.85);transform:translateX(-50%) rotate(3deg);border-left:2px dashed rgba(0,0,0,.12);border-right:2px dashed rgba(0,0,0,.12)}}
  .keystrip{{margin-top:26px;background:rgba(10,22,40,.74);border:1px solid rgba(90,160,240,.30);border-radius:18px;padding:24px 28px;font-size:33px;font-weight:600;color:#fff;line-height:1.4;display:flex;align-items:center;gap:18px}}
  .keystrip .kdot{{flex:0 0 auto;width:18px;height:18px;border-radius:50%;background:#3B9EFF;box-shadow:0 0 14px rgba(59,158,255,.8)}}
  .card{{margin-top:40px;background:rgba(10,22,40,.74);border:1px solid rgba(90,160,240,.30);border-radius:24px;padding:36px 38px}}
  .card .big{{font-size:54px;font-weight:800;color:#fff;line-height:1.2}}
  .card .asksub{{font-size:34px;color:rgba(255,255,255,.85);margin-top:14px;font-weight:600}}
  .pillrow{{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap}}
  .pill{{font-size:26px;font-weight:700;color:#3B9EFF;background:rgba(59,158,255,.14);border:1px solid rgba(59,158,255,.35);border-radius:999px;padding:14px 26px}}
  #karaoke{{position:absolute;left:56px;right:56px;bottom:110px;z-index:4;text-align:center}}
  .phrase{{display:inline-block;background:rgba(3,10,22,.68);border-radius:20px;padding:24px 32px;font-size:38px;font-weight:600;color:rgba(255,255,255,.93);line-height:1.5}}
  .kw{{transition:color .12s}}
  .kw.on{{color:#3B9EFF;font-weight:800}}
</style>
</head>
<body>
<div id="root" data-composition-id="daily" data-start="0" data-duration="{total}" data-width="1080" data-height="1920">
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
  tl.from('#b0-key', {{opacity:0, x:-18, duration:.45}}, 1.15);
  {"".join(chr(10) + "  " + x for x in trans)}
  {"".join(chr(10) + "  " + x for x in calls)}
  tl.to({{}}, {{duration:{total}}});
</script>
</body>
</html>
"""
    open(os.path.join(V2, f"{prefix}.html"), "w").write(html)
    variant = JINGLE_VARIANTS[doy % 4]
    print(f"{prefix}.html ditulis ({total}s, {len(words)} kata). Varian jingle hari ini: {variant}")
    print(f"VARIANT={variant}")

    # ---- tracking foto ----
    if not track:
        return 0
    try:
        used_p = os.path.join(BASE, "data", "used_images.json")
        used = json.load(open(used_p))
        bgs = [os.path.basename(b["photo"].replace("../assets/", "")) for b in beats[:-1]]
        used["today_video"] = bgs
        used["used"] = sorted(set(used.get("used", [])) | set(bgs))
        json.dump(used, open(used_p, "w"), indent=2)
        print("tracking foto:", bgs)
    except Exception as e:
        print(f"tracking foto skip: {e}")
    return 0


def mux(render_mp4, vo_mp3, out_mp4, variant):
    """Gabung render + VO + jingle varian -> mp4 faststart siap WhatsApp."""
    jingle = os.path.join(ASSETS, f"jingle-{variant}.wav")
    if not os.path.exists(jingle):
        jingle = os.path.join(ASSETS, "fastlis-jingle.wav")
    dur = audio_duration(vo_mp3)
    fade_st = max(0, round(dur - 2.5, 1))
    fc = (f"[1:a]volume=1.0[vo];[2:a]atrim=0:{round(dur + 1)},volume=0.12,"
          f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_st}:d=2.5[bg];"
          f"[vo][bg]amix=inputs=2:duration=longest:dropout_transition=0[a]")
    cp = subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", render_mp4, "-i", vo_mp3, "-i", jingle,
         "-filter_complex", fc, "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
         "-movflags", "+faststart", out_mp4],
        capture_output=True, text=True)
    if cp.returncode != 0:
        print("MUX GAGAL:", cp.stderr[-500:])
        return 1
    print("mux ok:", out_mp4, f"(jingle: {os.path.basename(jingle)})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--mux":
        # --mux <render_mp4> <vo_mp3> <out_mp4> ; varian dari VARIANT hari ini
        doy = today_wib().timetuple().tm_yday
        sys.exit(mux(sys.argv[2], sys.argv[3], sys.argv[4],
                     JINGLE_VARIANTS[doy % 4]))
    sys.exit(main())
