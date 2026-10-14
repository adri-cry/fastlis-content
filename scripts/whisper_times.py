#!/usr/bin/env python3
"""Transkripsi audio VO -> timestamp per kata (JSON ke stdout).

Dijalankan dengan venv whisper:
  ~/workspace/venvs/whisper/bin/python scripts/whisper_times.py <audio.mp3>

Butuh model lokal di ~/workspace/models/faster-whisper-small
(download sekali via curl karena huggingface_hub gagal parse proxy).
"""
import json
import os
import sys

MODEL_DIR = os.path.expanduser("~/workspace/models/faster-whisper-small")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "no audio"}))
        return 1
    from faster_whisper import WhisperModel
    import subprocess
    import numpy as np
    model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
    # decode manual via ffmpeg (bypass PyAV yang bermasalah) -> numpy PCM 16kHz mono
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", sys.argv[1],
         "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
        capture_output=True).stdout
    pcm = np.frombuffer(raw, dtype=np.float32)
    segments, _ = model.transcribe(pcm, language="id",
                                   word_timestamps=True, vad_filter=True)
    words = []
    for seg in segments:
        for w in (seg.words or []):
            words.append({"w": w.word.strip(), "t0": round(w.start, 3),
                          "t1": round(w.end, 3)})
    print(json.dumps(words, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
