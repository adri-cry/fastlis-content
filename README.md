# FastLIS Content Pipeline

Otomasi pembuatan konten Instagram harian untuk **FastLIS** (sistem informasi
laboratorium / LIS untuk analis kesehatan di Indonesia).

Setiap pagi pipeline ini membuat dua paket konten dari satu topik edukasi
seputar dunia laboratorium:

- **Carousel + single post** (gambar, 1080×1920)
- **Video reels** (gaya whiteboard hand-drawn, dengan voice over + musik)

## Cara Kerja

```
Topik baru tiap hari
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│ Konten gambar   │     │ Video reels      │
│ 5 slide +       │     │ whiteboard       │
│ 1 single post   │     │ + voice over     │
└─────────────────┘     └──────────────────┘
        │                        │
        ▼                        ▼
   Review → arsip → publikasi
```

1. **Pilih topik.** Topik harus baru (dicek terhadap riwayat 30 hari) dan
   formatnya digilir: kuis, before-vs-after, mitos-vs-fakta, tips praktis,
   checklist.
2. **Render gambar.** Carousel 5 slide + 1 single post, lengkap dengan foto
   yang relevan tiap slide dan caption siap posting.
3. **Quality check otomatis.** Memastikan foto sesuai isi slide, tidak ada
   foto ganda, caption tidak kepanjangan, dan slide terakhir berupa kartu
   penutup.
4. **Render video.** Naskah 6 bagian diubah menjadi animasi whiteboard dengan
   voice over, teks karaoke yang mengikuti suara, dan musik latar.
5. **Review.** Semua hasil dikirim untuk direview sebelum dipublikasikan.

## Struktur Folder

```
fastlis-content/
├── assets/        # Logo dan aset brand
├── carousel/      # Template desain carousel
├── single/        # Template desain single post
├── content/       # Konten hari ini (teks, judul, naskah video)
├── data/          # Data pelacakan: riwayat topik, foto terpakai
├── docs/          # Dokumentasi dan materi referensi
├── html/          # Bank foto laboratorium + font
├── reels/         # Aset dan template video (musik, efek suara, font)
├── scripts/       # Script otomasi pipeline
│   └── tools/     # Script bantu sekali pakai (pembuat musik/efek suara)
└── backups/       # Arsip template versi lama
```

## Menjalankan Manual

Butuh Python 3 dan Google Chrome terinstal.

```bash
# 1. Siapkan file konten hari ini di content/hari-ini.json
#    (lihat contoh struktur di file yang sudah ada)

# 2. Render gambar (carousel + single post + QA)
python3 scripts/render_all.py

# 3. Render video reels
python3 scripts/build_reels_whiteboard.py --tulis-naskah  # tulis naskah dulu
python3 scripts/build_reels_whiteboard.py --daily         # bangun animasi
python3 scripts/render_reels.py --html v2/daily.html --out v2/daily_raw.mp4 --duration <detik>
python3 scripts/build_reels_whiteboard.py --mux reels/v2/daily_raw.mp4 reels/v2/vo_daily.mp3 hasil.mp4
```

Hasil render harian **tidak** disimpan di repo ini (lihat `.gitignore`).
Distribusinya lewat dashboard web dan arsip lokal.

## Standar Konten

- Bahasa Indonesia, santai tapi profesional, untuk analis lab
- Istilah baku: **"kritis"** (nilai kritis, batas kritis) — bukan "panik"
- Cover carousel berupa pertanyaan yang memancing rasa penasaran
- Setiap slide memakai foto yang sesuai dengan isi slide tersebut
- Minimal satu slide berisi data konkret (angka/rentang) yang layak disimpan
- Ajakan di akhir spesifik (simpan, tandai teman, komentar)

## Catatan Teknis

- Semua tanggal memakai zona waktu WIB (Asia/Jakarta)
- Render video memakai [Hyperframes](https://github.com/) 0.8.31 (sudah termasuk di `reels/`)
- Screenshot memakai Chrome DevTools Protocol (`scripts/cdp_shot.py`)
- Font dan library animasi disertakan lokal di `reels/assets/` (tidak butuh internet saat render)
- Video output memakai flag `faststart` agar bisa diputar di WhatsApp/Instagram
