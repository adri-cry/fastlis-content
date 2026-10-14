#!/usr/bin/env python3
"""Reels v2 versi panjang (~2 menit). Naskah ditulis manual di BEATS.

Pakai: python3 scripts/build_reels_v2_long.py
Render: cd reels && TMPDIR=$PWD/.tmp npx hyperframes render -c v2/long.html -o v2/long_raw.mp4
Mux:    python3 scripts/build_reels_v2.py --mux reels/v2/long_raw.mp4 reels/v2/vo_long.mp3 <out.mp4>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_reels_v2 as B

HL = 'class="hl"'


def T(line1, line2):
    return f'{line1}<br><span {HL}>{line2}</span>'


BEATS = [
    dict(label="PRE-ANALITIK",
         title=T("SERUM PASIEN KAMU", "KOK MERAH BANGET?"),
         narr="Serum pasien kamu kok merah banget? Kenalin HIL, biang keroknya.",
         key="Kenalin HIL, biang keroknya.",
         kw=["serum", "tabung", "darah"], bg=""),
    dict(label="TIGA PENGACAU",
         title=T("HEMOLISIS, LIPEMIA,", "IKTERUS"),
         narr="Hemolisis, Lipemia, Ikterus. Tiga pengganggu hasil lab yang asalnya dari pre-analitik.",
         key="Tiga pengganggu hasil lab dari pre-analitik.",
         kw=["pre-analitik", "tabung", "pengambilan", "sampel"], bg=""),
    dict(label="SEL DARAH PECAH",
         title=f'01 &middot; <span {HL}>HEMOLISIS</span>',
         narr=("Satu. Hemolisis. Sel darah pecah, serum jadi merah. "
               "Biang keroknya: tourniquet kelamaan, jarum kekecilan, atau tabung dikocok."),
         key="Tourniquet kelamaan, jarum kekecilan, tabung dikocok.",
         kw=["pengambilan", "pipet", "tabung darah", "pre-analitik"], bg=""),
    dict(label="CEGAH HEMOLISIS",
         title=T("CARA CEGAH", "HEMOLISIS"),
         narr=("Dua. Cara cegahnya. Tourniquet maksimal satu menit. "
               "Pakai jarum 21 sampai 22G. "
               "Balik tabung delapan sampai sepuluh kali, pelan. Jangan dikocok."),
         key="Tourniquet maks 1 menit, jarum 21-22G, balik 8-10x pelan.",
         kw=["pengambilan", "tabung", "pre-analitik", "sampel"], bg=""),
    dict(label="LEMAK DARAH TINGGI",
         title=f'03 &middot; <span {HL}>LIPEMIA</span>',
         narr=("Tiga. Lipemia. Serum keruh kayak susu. Penyebabnya lemak darah tinggi. "
               "Pasien nggak puasa, atau lagi dapat nutrisi parenteral."),
         key="Lemak darah tinggi: pasien nggak puasa / nutrisi parenteral.",
         kw=["serum", "tabung", "sampel", "rak"], bg=""),
    dict(label="ATASI LIPEMIA",
         title=T("CARA ATASI", "LIPEMIA"),
         narr=("Empat. Cara atasinya. Minta pasien puasa delapan sampai dua belas jam "
               "sebelum diambil. Kalau masih keruh, catat lipemik dan diskusikan dengan dokter. Ultrasentrifugasi bisa jadi opsi terakhir untuk lipemia berat, sesuai SOP lab."),
         key="Puasa 8-12 jam sebelum ambil; catat lipemik.",
         kw=["tabung", "sampel", "rak", "reagen"], bg=""),
    dict(label="BILIRUBIN TINGGI",
         title=f'05 &middot; <span {HL}>IKTERUS</span>',
         narr=("Lima. Ikterus. Serum kuning pekat, tandanya bilirubin tinggi. "
               "Jangan asal encerkan. Catat ikterik di LIS supaya hasilnya bisa diinterpretasi dengan benar."),
         key="Serum kuning pekat: catat ikterik di LIS.",
         kw=["serum", "tabung", "sampel", "reagen"], bg=""),
    dict(label="DETEKSI OTOMATIS",
         title=T("DETEKSI", "HIL INDEX"),
         narr=("Enam. Deteksi. Analyzer modern punya HIL index. "
               "Kadar hemolisis, lipemia, dan ikterus diukur otomatis di setiap sampel. Kalau indeksnya tinggi, analyzer kasih flag. Jangan diabaikan, itu peringatan."),
         key="HIL index: hemolisis, lipemia, ikterus terukur otomatis.",
         kw=["analyzer", "alat", "otomasi", "mesin"], bg=""),
    dict(label="KEPUTUSAN LAB",
         title=T("KAPAN SAMPEL", "DITOLAK?"),
         narr=("Tujuh. Keputusan. Kapan sampel harus ditolak? "
               "Kalau HIL-nya mengganggu hasil kritis, misalnya kalium. "
               "Tolak, minta ambil ulang, dan jelaskan alasannya. Dokumentasikan penolakan di LIS. Komunikasi yang jelas mencegah kejadian terulang."),
         key="Ganggu hasil kritis (mis. kalium)? Tolak, ambil ulang.",
         kw=["tabung", "sampel", "pre-analitik", "rak"], bg=""),
    dict(label="PENUTUP",
         title=T("PERNAH KETIPU", "HASIL LAB?"),
         narr=("Pernah hasil lab bikin bingung gara-gara HIL? Ceritain pengalamanmu di kolom komentar. "
               "Follow FastLIS untuk edukasi lab setiap hari."),
         promo="Follow FastLIS untuk edukasi lab setiap hari.",
         bg="",
         pills="".join(f'<span class="pill">{p}</span>' for p in
                       ["Ceritain di komen", "Save buat jaga-jaga", "Tag teman lab"]),
         ask_sub="Pernah hasil lab bikin bingung gara-gara HIL?"),
]

if __name__ == "__main__":
    doy = B.today_wib().timetuple().tm_yday
    sys.exit(B.build_from_beats(BEATS, "long", doy, track=False, ignore_used=True))
