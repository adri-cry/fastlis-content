#!/usr/bin/env python3
"""Synth SFX untuk reels whiteboard (100% numpy, tanpa aset eksternal).
pop, ding, scribble, swoosh, tick -> reels/assets/sfx-*.wav (44.1kHz mono).
"""
import os
import numpy as np
from scipy.io import wavfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "reels", "assets")
SR = 44100


def _w(name, y):
    y = y / max(1e-9, np.abs(y).max()) * 0.9
    wavfile.write(os.path.join(OUT, f"sfx-{name}.wav"), SR,
                  (y * 32767).astype(np.int16))
    print("sfx-", name, len(y) / SR, "dtk", sep="")


def pop():
    t = np.arange(int(SR * 0.16)) / SR
    f = 400 + 2500 * t
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)
    _w("pop", y)


def ding():
    t = np.arange(int(SR * 0.7)) / SR
    y = (np.sin(2 * np.pi * 880 * t) * 0.6 +
         np.sin(2 * np.pi * 1318.5 * t) * 0.3 +
         np.sin(2 * np.pi * 1760 * t) * 0.1) * np.exp(-t * 7)
    _w("ding", y)


def _noise(n):
    return np.random.default_rng(7).standard_normal(n)


def scribble():
    n = int(SR * 0.45)
    y = _noise(n)
    # bandpass kasar 2-6kHz via diferensiasi + smoothing
    y = np.diff(y, prepend=0)
    k = np.ones(8) / 8
    y = np.convolve(y, k, mode="same")
    env = np.minimum(1, np.arange(n) / (SR * 0.05)) * np.minimum(
        1, (n - np.arange(n)) / (SR * 0.08))
    _w("scribble", y * env)


def swoosh():
    n = int(SR * 0.45)
    t = np.arange(n) / SR
    y = _noise(n)
    k = np.ones(32) / 32
    y = np.convolve(y, k, mode="same")
    env = np.sin(np.pi * t / (n / SR)) ** 2
    _w("swoosh", y * env)


def tick():
    t = np.arange(int(SR * 0.06)) / SR
    y = np.sin(2 * np.pi * 2100 * t) * np.exp(-t * 90)
    _w("tick", y)


if __name__ == "__main__":
    pop()
    ding()
    scribble()
    swoosh()
    tick()
