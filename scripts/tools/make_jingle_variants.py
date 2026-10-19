#!/usr/bin/env python3
"""4 variasi jingle FastLIS dari MOTIF yang sama (melodi + akor identik),
aransemen beda biar tidak bosan tapi identitas audio tetap terjaga.
100% sintesis numpy, tanpa sample pihak ketiga.

Variasi:
  original  - 100 BPM, full band (seperti fastlis-jingle.wav sekarang)
  chill     -  84 BPM, pad + petikan saja, tanpa drum (cocok di bawah VO santai)
  energetic - 112 BPM, drum lebih nendang, lead lebih bright
  minimal   -  92 BPM, motif lead + pad lembut, sparse (cocok VO padat)

Output: reels/assets/jingle-<nama>.wav
"""
import importlib.util
import os
import wave

import numpy as np

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "make_jingle.py")
_m = importlib.util.spec_from_file_location("mj", SPEC)
mj = importlib.util.module_from_spec(_m)
_m.loader.exec_module(mj)

SR = mj.SR
ASSETS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "reels", "assets"))


def build(bpm=100, pad_lvl=0.20, bass_lvl=0.34, arp_lvl=0.30, lead_lvl=0.38,
          drums=True, drum_lvl=1.0, lead=True, arp=True, bass=True,
          dur=35.5, fade_in=0.6, fade_out=2.5):
    beat = 60.0 / bpm
    bar = beat * 4
    n_bars = int(dur / bar)
    n = int(dur * SR)
    L = np.zeros(n)
    R = np.zeros(n)

    def stereo(y, at, level=1.0, pan=0.0, detune_cents=0.0):
        i = int(at * SR)
        j = min(n, i + len(y))
        if j <= i:
            return
        seg = y[:j - i] * level
        if detune_cents:
            ph = 2 * np.pi * detune_cents / 100 / 12
            l = seg * np.cos(ph / 2)
            r = seg * np.cos(ph / 2)
            q = np.concatenate([[0], np.diff(seg)]) * 0.15
            l = l - q
            r = r + q
        else:
            l = r = seg
        gl = np.sqrt(max(0.0, 1 - pan))
        gr = np.sqrt(max(0.0, 1 + pan))
        L[i:j] += l * gl
        R[i:j] += r * gr

    chords = mj.CHORDS[:n_bars]
    roots = (mj.ROOTS * ((n_bars // len(mj.ROOTS)) + 1))[:n_bars]

    # PAD
    for b, (name, tones) in enumerate(chords):
        t0 = b * bar
        chord = np.zeros(int(bar * SR))
        for mt in tones:
            chord += mj.tone(mj.midi(mt), bar, "pad", harm=(1.0, 0.5, 0.25)) / len(tones)
        stereo(chord, t0, level=pad_lvl, detune_cents=6)

    # BASS pump 8th
    if bass:
        for b, root in enumerate(roots):
            for e in range(8):
                at = b * bar + e * beat / 2
                y = mj.tone(mj.midi(root - 12), beat / 2 * 0.95, "bass", harm=(1.0, 0.4))
                stereo(y, at, level=bass_lvl)

    # ARP
    if arp:
        for b, (name, tones) in enumerate(chords):
            cyc = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 12]
            for e in range(8):
                m = cyc[e % 4]
                y = mj.tone(mj.midi(m), beat / 2 * 0.9, "pluck", harm=(1.0, 0.35))
                stereo(y, b * bar + e * beat / 2, level=arp_lvl,
                       pan=0.12 if e % 2 == 0 else -0.12)

    # LEAD (motif identitas, nada sama persis)
    if lead:
        for m, sb, db in mj.LEAD:
            at = sb * beat
            if at >= dur:
                continue
            lvl = lead_lvl * (0.8 if sb >= 48 else 1.0)
            y = mj.tone(mj.midi(m), db * beat * 0.96, "lead", harm=(1.0, 0.3, 0.12))
            nn = len(y)
            tt = np.arange(nn) / SR
            y = y * (1 + 0.06 * np.sin(2 * np.pi * 5.5 * tt))
            stereo(y, at, level=lvl)

    # DRUMS
    if drums:
        for b in range(n_bars):
            t0 = b * bar
            if b < 2:
                stereo(mj.kick(), t0, level=0.42 * drum_lvl)
                stereo(mj.kick(), t0 + 2 * beat, level=0.38 * drum_lvl)
                for e in range(8):
                    stereo(mj.hat(), t0 + e * beat / 2, level=0.10 * drum_lvl)
            else:
                for q in range(4):
                    stereo(mj.kick(), t0 + q * beat, level=0.50 * drum_lvl)
                stereo(mj.snare(), t0 + 1 * beat, level=0.30 * drum_lvl)
                stereo(mj.snare(), t0 + 3 * beat, level=0.30 * drum_lvl)
                for e in range(8):
                    stereo(mj.hat(), t0 + e * beat / 2, level=0.13 * drum_lvl)
                stereo(mj.hat(0.12, open_=True), t0 + 3.5 * beat, level=0.12 * drum_lvl)

    # mastering
    mix = np.stack([L, R])
    mix = np.tanh(mix * 1.1)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix *= 0.89 / peak
    nf = int(fade_in * SR)
    mix[:, :nf] *= np.linspace(0, 1, nf)
    nfo = int(fade_out * SR)
    mix[:, -nfo:] *= np.linspace(1, 0, nfo)
    return mix


VARIANTS = {
    "original": dict(bpm=100),
    "chill": dict(bpm=84, bass=False, drums=False, arp_lvl=0.22,
                  pad_lvl=0.26, lead_lvl=0.30, fade_in=1.5),
    "energetic": dict(bpm=112, drum_lvl=1.25, lead_lvl=0.44, arp_lvl=0.32),
    "minimal": dict(bpm=92, bass=False, drums=False, arp=False,
                    pad_lvl=0.22, lead_lvl=0.34, fade_in=1.2),
}


def main():
    for name, kw in VARIANTS.items():
        mix = build(**kw)
        out = os.path.join(ASSETS, f"jingle-{name}.wav")
        pcm = (mix * 32767).astype(np.int16)
        with wave.open(out, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.T.copy().tobytes())
        print("ditulis:", out)


if __name__ == "__main__":
    main()
