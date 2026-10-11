#!/usr/bin/env python3
"""Jingle original FastLIS — upbeat corporate tech, 35 detik, 100 BPM.
100% hasil sintesis (numpy), tanpa sample pihak ketiga. Bebas dipakai.
Output: reels/assets/fastlis-jingle.wav (44.1kHz stereo 16-bit).
"""
import os
import numpy as np

SR = 44100
BPM = 100
BEAT = 60.0 / BPM          # 0.6 dtk
BAR = BEAT * 4             # 2.4 dtk
N_BARS = 14
DUR = 35.5

def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def env_ad(n, a, d, s_level=0.0, r=0.0):
    """Amplop attack-decay(-sustain-release sederhana)."""
    e = np.ones(n)
    na = max(1, int(a * SR)); nd = max(1, int(d * SR))
    e[:na] = np.linspace(0, 1, na)
    e[na:na + nd] = np.linspace(1, s_level, nd)
    if r > 0 and na + nd < n:
        nr = max(1, int(r * SR))
        tail = np.linspace(s_level, 0, min(nr, n - na - nd))
        e[na + nd:na + nd + len(tail)] = tail
        e[na + nd + len(tail):] = 0
    else:
        e[na + nd:] = s_level
    return e

def tone(freq, dur, kind="sine", harm=(1.0,)):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for i, h in enumerate(harm, start=1):
        y += h * np.sin(2 * np.pi * freq * i * t) / max(1, i * 0.7)
    if kind == "pluck":
        y *= env_ad(n, 0.005, dur * 0.9)
    elif kind == "pad":
        y *= env_ad(n, 0.4, dur * 0.5, s_level=0.7, r=0.6)
    elif kind == "bass":
        y *= env_ad(n, 0.008, dur * 0.85)
    elif kind == "lead":
        y *= env_ad(n, 0.02, dur * 0.6, s_level=0.75, r=0.15)
    return y

def place(track, y, at_sec):
    i = int(at_sec * SR)
    j = min(len(track), i + len(y))
    if j > i:
        track[i:j] += y[:j - i]

def kick(dur=0.28):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 150 * np.exp(-t * 22) + 44
    y = np.sin(2 * np.pi * np.cumsum(f) / SR)
    return y * env_ad(n, 0.002, dur * 0.95)

def snare(dur=0.18):
    n = int(dur * SR)
    noise = np.random.default_rng(7).standard_normal(n)
    y = 0.6 * noise * env_ad(n, 0.001, dur * 0.9) + 0.4 * np.sin(2 * np.pi * 190 * np.arange(n) / SR) * env_ad(n, 0.001, 0.08)
    return y

def hat(dur=0.05, open_=False):
    n = int(dur * SR)
    rng = np.random.default_rng(21)
    noise = rng.standard_normal(n)
    # highpass kasar: kurangi low-freq
    y = noise - np.convolve(noise, np.ones(8) / 8, mode="same")
    return y * env_ad(n, 0.001, dur * (0.95 if open_ else 0.7))

# ---- progresi akor: C G Am F | C G F G | C G Am F | C F G C ----
CHORDS = [
    ("C", [48, 52, 55, 60]), ("G", [43, 47, 50, 55]),
    ("Am", [45, 48, 52, 57]), ("F", [41, 45, 48, 53]),
    ("C", [48, 52, 55, 60]), ("G", [43, 47, 50, 55]),
    ("F", [41, 45, 48, 53]), ("G", [43, 47, 50, 55]),
    ("C", [48, 52, 55, 60]), ("G", [43, 47, 50, 55]),
    ("Am", [45, 48, 52, 57]), ("F", [41, 45, 48, 53]),
    ("C", [48, 52, 55, 60]), ("G", [43, 47, 50, 62]),
]
ROOTS = [48, 43, 45, 41, 48, 43, 41, 43, 48, 43, 45, 41, 48, 43]

# ---- melodi lead (midi, beat_mulai, dur_beat) — komposisi original ----
LEAD = [
    (76, 0, 1), (79, 1, 1), (81, 2, 2),
    (79, 4, 1), (76, 5, 1), (74, 6, 2),
    (76, 8, 1), (79, 9, 1), (81, 10, 1), (84, 11, 1),
    (83, 12, 2), (79, 14, 2),
    (84, 16, 1), (81, 17, 1), (79, 18, 2),
    (81, 20, 1), (79, 21, 1), (76, 22, 2),
    (74, 24, 1), (76, 25, 1), (79, 26, 2),
    (81, 28, 3),
    (76, 32, 1), (79, 33, 1), (81, 34, 2),
    (84, 36, 1), (83, 37, 1), (81, 38, 2),
    (79, 40, 1), (81, 41, 1), (84, 42, 1), (86, 43, 1),
    (84, 44, 4),
    (83, 48, 1), (81, 49, 1), (79, 50, 2),
    (76, 52, 1), (74, 53, 1), (72, 54, 2),
]

def main():
    n = int(DUR * SR)
    L = np.zeros(n); R = np.zeros(n)

    def stereo(y, at, level=1.0, pan=0.0, detune_cents=0.0):
        i = int(at * SR); j = min(n, i + len(y))
        if j <= i:
            return
        seg = y[:j - i] * level
        if detune_cents:
            # pelebaran stereo sederhana: fasa beda tipis L/R
            ph = 2 * np.pi * detune_cents / 100 / 12
            l = seg * np.cos(ph / 2); r = seg * np.cos(ph / 2)
            # tambah komponen quadrature kecil utk rasa lebar
            q = np.concatenate([[0], np.diff(seg)]) * 0.15
            l = l - q; r = r + q
        else:
            l = r = seg
        gl = np.sqrt(max(0.0, 1 - pan)); gr = np.sqrt(max(0.0, 1 + pan))
        L[i:j] += l * gl; R[i:j] += r * gr

    # ---- PAD: akor penuh tiap bar ----
    for b, (name, tones) in enumerate(CHORDS):
        t0 = b * BAR
        chord = np.zeros(int(BAR * SR))
        for m in tones:
            chord += tone(midi(m), BAR, "pad", harm=(1.0, 0.5, 0.25)) / len(tones)
        stereo(chord, t0, level=0.20, detune_cents=6)

    # ---- BASS: pump 8th ----
    for b, root in enumerate(ROOTS):
        for e in range(8):
            at = b * BAR + e * BEAT / 2
            y = tone(midi(root - 12), BEAT / 2 * 0.95, "bass", harm=(1.0, 0.4))
            stereo(y, at, level=0.34)

    # ---- ARP: bar 1-2 quarter, sisanya 8th naik ----
    for b, (name, tones) in enumerate(CHORDS):
        cyc = [tones[0] + 12, tones[1] + 12, tones[2] + 12, tones[1] + 12]
        if b < 2:
            steps = [(0, cyc[0]), (2, cyc[2])]
            for beat_off, m in steps:
                y = tone(midi(m), BEAT * 0.9, "pluck", harm=(1.0, 0.35))
                stereo(y, b * BAR + beat_off * BEAT, level=0.26, pan=0.15)
        else:
            for e in range(8):
                m = cyc[e % 4]
                y = tone(midi(m), BEAT / 2 * 0.9, "pluck", harm=(1.0, 0.35))
                stereo(y, b * BAR + e * BEAT / 2, level=0.30, pan=0.12 if e % 2 == 0 else -0.12)

    # ---- LEAD ----
    for m, sb, db in LEAD:
        if sb >= 48:  # outro lebih lembut
            lvl = 0.30
        elif sb < 8:
            lvl = 0.0  # lead masuk bar 3
            continue
        else:
            lvl = 0.38
        y = tone(midi(m), db * BEAT * 0.96, "lead", harm=(1.0, 0.3, 0.12))
        # vibrato halus
        nn = len(y); tt = np.arange(nn) / SR
        y = y * (1 + 0.06 * np.sin(2 * np.pi * 5.5 * tt))
        stereo(y, sb * BEAT, level=lvl)

    # ---- DRUM ----
    for b in range(N_BARS):
        t0 = b * BAR
        if b < 2:  # intro minimal
            stereo(kick(), t0, level=0.42)
            stereo(kick(), t0 + 2 * BEAT, level=0.38)
            for e in range(8):
                stereo(hat(), t0 + e * BEAT / 2, level=0.10)
        else:
            for q in range(4):
                stereo(kick(), t0 + q * BEAT, level=0.50)
            stereo(snare(), t0 + 1 * BEAT, level=0.30)
            stereo(snare(), t0 + 3 * BEAT, level=0.30)
            for e in range(8):
                stereo(hat(), t0 + e * BEAT / 2, level=0.13)
            stereo(hat(0.12, open_=True), t0 + 3.5 * BEAT, level=0.12)

    # ---- mastering: soft clip, normalisasi, fade ----
    for ch in (L, R):
        pass
    mix = np.stack([L, R])
    mix = np.tanh(mix * 1.1)
    peak = np.max(np.abs(mix))
    if peak > 0:
        mix *= 0.89 / peak
    nf = int(0.6 * SR)
    mix[:, :nf] *= np.linspace(0, 1, nf)
    nfo = int(2.5 * SR)
    mix[:, -nfo:] *= np.linspace(1, 0, nfo)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "reels", "assets", "fastlis-jingle.wav")
    out = os.path.normpath(out)
    import wave
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.T.copy().tobytes())
    print("jingle ditulis:", out, f"({DUR}s)")

if __name__ == "__main__":
    main()
